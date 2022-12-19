import re
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterator, Type

import pytest

from .auto_benchmarker import (
    AutoBenchmarker,
    BaseOutputData,
    BaseTestModel,
    PytestConfig,
)


# TODO: benchmark.json, benchmark_test_*.py pattern


def benchmark_test(pytest_config: PytestConfig):
    def decorator(fn):
        fn.pytest_config = pytest_config
        fn.benchmark_test = True
        return fn

    return decorator


class JSONItem(pytest.Item):
    def __init__(
        self,
        *,
        func_name: str,
        data: BaseOutputData,
        benchmarker: AutoBenchmarker,
        acceptable_st_devs: int,
        acceptable_re_runs: int,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.benchmarker = benchmarker
        self.data = data
        self.func_name = func_name
        self.acceptable_st_devs = acceptable_st_devs
        self.add_marker(pytest.mark.flaky(reruns=acceptable_re_runs))

    def runtest(self):
        self.benchmarker.test_benchmark_data(
            benchmark_data=self.data,
            acceptable_st_devs=self.acceptable_st_devs,
            func_name=self.func_name,
        )


class JSONFile(pytest.File):
    model: Type[BaseTestModel]

    def __init__(
        self,
        *,
        benchmarkers: Iterator[AutoBenchmarker],
        benchmark_dir: Callable[[AutoBenchmarker], Path],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.benchmarkers = benchmarkers
        self.benchmark_dir = benchmark_dir

    def collect(self):
        for benchmarker in self.benchmarkers:
            pytest_config = benchmarker.pytest_config
            model = benchmarker.test_model

            test_model = model.parse_file(
                self.benchmark_dir(benchmarker) / "benchmark.json"
            )
            for func_name, test in test_model.tests:
                for i, data in enumerate(test):
                    yield JSONItem.from_parent(
                        self,
                        name=f"{func_name}_{i}",
                        func_name=func_name,
                        data=data,
                        benchmarker=benchmarker,
                        acceptable_st_devs=pytest_config.acceptable_st_devs,
                        acceptable_re_runs=pytest_config.re_runs,
                    )


def get_benchmarkers_from_definition(file_path: Path) -> Iterator[AutoBenchmarker]:
    import importlib.util
    import sys
    from inspect import getmembers, isfunction

    spec = importlib.util.spec_from_file_location("autobenchmarker", file_path)
    assert spec is not None
    autobench = importlib.util.module_from_spec(spec)
    sys.modules["autobenchmarker"] = autobench
    assert spec.loader is not None
    spec.loader.exec_module(autobench)

    def is_benchmark_test(fn):
        return isfunction(fn) and getattr(fn, "benchmark_test", False)

    config_and_funcs: defaultdict[PytestConfig, dict[str, Callable]] = defaultdict(dict)
    for func_name, func in getmembers(autobench, is_benchmark_test):
        pytest_config = func.pytest_config
        config_and_funcs[pytest_config][func_name] = func
    assert config_and_funcs, "No benchmark test functions found!"

    for pytest_config, funcs in config_and_funcs.items():
        yield AutoBenchmarker(pytest_config, **funcs)


def find_benchmarks(start_path: Path) -> Iterator[AutoBenchmarker]:
    for f in start_path.glob("benchmark_test_*.py"):
        yield from get_benchmarkers_from_definition(f)


def get_benchmark_dir(start_path: Path, auto_benchmarker: AutoBenchmarker) -> Path:
    # Use either defined path or a directory of the same name as the
    # benchmark definition file
    pytest_config = auto_benchmarker.pytest_config
    return start_path / pytest_config.benchmark_path


def pytest_sessionstart(session: pytest.Session):
    for auto_benchmarker in find_benchmarks(session.startpath):
        benchmark_dir = get_benchmark_dir(session.startpath, auto_benchmarker)

        if not benchmark_dir.exists() or session.config.option.genbenchmark:
            auto_benchmarker.generate_benchmark(verbose=True)
        else:
            benchmark_sub_path = benchmark_dir / "benchmark.json"
            if not benchmark_sub_path.exists():
                auto_benchmarker.generate_benchmark(verbose=True)


def pytest_collect_file(parent: pytest.Session, file_path: Path):
    if re.match(r"benchmark_test_(.+).py", file_path.name):
        # TODO: let it through if there's no actual benchmark there - maybe just a similar name
        auto_benchmarkers = get_benchmarkers_from_definition(file_path)
        return JSONFile.from_parent(
            parent,
            path=file_path,
            benchmarkers=auto_benchmarkers,
            benchmark_dir=lambda b: get_benchmark_dir(parent.startpath, b),
        )


def pytest_addoption(parser):
    parser.addoption(
        "--generatebenchmark",
        dest="genbenchmark",
        action="store_true",
        help="Should (re)generate benchmark?",
    )
