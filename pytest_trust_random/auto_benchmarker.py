import json
import time
from multiprocessing import cpu_count
from pathlib import Path
from typing import Callable, Type

from pydantic import create_model

from .base_models import (
    BaseOutputData,
    BaseTestModel,
    GlobalSettingsModel,
    PytestConfig,
)
from .func_benchmarker import FuncBenchmarker
from .setup_func_benchmarker import SetupFuncBenchmarker

# From here on we will only use benchmarker_test_func and StateStats

"""
This is a prototype auto benchmarker

TODO: Future feature, support enums in functions and iterate over each possibility

Note - eventually make autobenchmarker and funcbenchmarker inherit from benchmarker
"""


class AutoBenchmarker:
    def __init__(self, pytest_config: PytestConfig, **funcs: Callable) -> None:
        assert pytest_config, "No pytest_config!"
        self.pytest_config = pytest_config
        self.setup_func_benchmarkers = {
            k: SetupFuncBenchmarker(v) for k, v in funcs.items()
        }
        self._settings_model = None
        self._settings = None
        self._test_model = None
        self._func_benchmarkers = None
        self.settings_folder = Path(self.pytest_config.benchmark_path)

    def __str__(self) -> str:
        return ", ".join(
            name + str(i) for name, i in self.setup_func_benchmarkers.items()
        )

    def _generate_test_model(self) -> Type[BaseTestModel]:
        output_models_dict = {
            func_name: (list[setup_func_benchmarker.output_model], ...)  # type:ignore
            for func_name, setup_func_benchmarker in self.setup_func_benchmarkers.items()
        }
        return create_model(
            "TestData",
            __base__=BaseTestModel,
            tests=(create_model("FuncData", **output_models_dict), ...),  # type:ignore
        )

    @property
    def test_model(self) -> Type[BaseTestModel]:
        if self._test_model is None:
            self._test_model = self._generate_test_model()
        return self._test_model

    def _generate_settings_model(self) -> Type[GlobalSettingsModel]:
        settings_dict = {}
        for func_name, func_benchmarker in self.setup_func_benchmarkers.items():
            settings_dict[func_name] = (func_benchmarker.settings_model, ...)
        return create_model(
            "GlobalSettings", __base__=GlobalSettingsModel, **settings_dict
        )

    @property
    def settings_model(self) -> Type[GlobalSettingsModel]:
        if self._settings_model is None:
            self._settings_model = self._generate_settings_model()
        return self._settings_model

    def _generate_settings_file(self, settings_path: Path) -> None:
        model = self.settings_model
        model_dict = {}
        for k, v in self.setup_func_benchmarkers.items():
            print(f"Attributes for function {k}:")
            model_dict[k] = v.generate_settings_instance()

        settings = model.parse_obj(model_dict)
        settings_file = open(settings_path, "w+")
        json.dump(settings.dict(), settings_file, indent=2)

    @property
    def settings(self) -> GlobalSettingsModel:
        if self._settings is None:
            settings_path = self.settings_folder / "settings.json"
            if not settings_path.exists():
                if not self.settings_folder.exists():
                    self.settings_folder.mkdir(parents=True)
                self._generate_settings_file(settings_path)
            self._settings = self.settings_model.parse_file(settings_path)
        return self._settings

    @property
    def func_benchmarkers(self) -> dict[str, FuncBenchmarker]:
        if self._func_benchmarkers is None:
            self._func_benchmarkers = {
                func_name: FuncBenchmarker(
                    getattr(self.settings, func_name), func_setup
                )
                for func_name, func_setup in self.setup_func_benchmarkers.items()
            }
        return self._func_benchmarkers

    def generate_benchmark(self, verbose: bool = False):
        func_benchmarkers = self.func_benchmarkers

        if verbose:
            total_benchmark_time = 0
            test_times = []
            total_tests = 0
            for func_benchmarker in func_benchmarkers.values():
                (
                    est_test_time,
                    est_benchmark_time,
                ) = func_benchmarker.estimate_computation_time()
                total_benchmark_time += est_benchmark_time
                total_tests += len(func_benchmarker)
                test_times.append(est_test_time)
            total_test_time = sum(test_times)
            print(f"Benchmark will run {total_tests} tests")
            print(f"Estimated benchmark calc time (one core): {total_benchmark_time}")
            print(
                f"Estimated benchmark calc time (multiple cores): {total_benchmark_time/cpu_count()}"
            )
            print(f"Estimated total test time (no reruns): {total_test_time}")

        start = time.time()
        all_benchmarks_out = {}
        for func_name, func_benchmarker in func_benchmarkers.items():
            benchmark_out = func_benchmarker.generate_benchmark()
            all_benchmarks_out[func_name] = benchmark_out
        end = time.time()

        if verbose:
            print(f"Benchmark calculated in: {end-start}")
        print()
        test_data = self.test_model.parse_obj({"tests": all_benchmarks_out})

        with open(self.settings_folder / "benchmark.json", "w+") as benchmark_file:
            json.dump(test_data.dict(), benchmark_file, indent=2)

        # hash_file_path = Path(str(self.settings_folder) + os.sep + "data_hash.txt")
        # with open(hash_file_path, "w+") as f:
        #    f.write(str(self))

    def test_benchmark_data(
        self, benchmark_data: BaseOutputData, acceptable_st_devs: float, func_name: str
    ) -> None:
        func_benchmarker = self.func_benchmarkers[func_name]
        func_benchmarker.test_benchmark_data(benchmark_data, acceptable_st_devs)
