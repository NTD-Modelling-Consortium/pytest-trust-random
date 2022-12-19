from pathlib import Path
from typing import Iterator, Type
import re

import pytest

from .auto_benchmarker import (
    AutoBenchmarker,
    BaseOutputData,
    BaseTestModel,
)


class JSONItem(pytest.Item):
    def __init__(
        self,
        *,
        func_name: str,
        data: BaseOutputData,
        benchmarker: AutoBenchmarker,
        acceptable_st_devs: int,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.benchmarker = benchmarker
        self.data = data
        self.func_name = func_name
        self.acceptable_st_devs = acceptable_st_devs

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
        model: Type[BaseTestModel],
        benchmarker: AutoBenchmarker,
        benchmark_dir: Path,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model = model
        self.benchmarker = benchmarker
        self.benchmark_dir = benchmark_dir
        self.acceptable_st_devs = benchmarker.pytest_config.acceptable_st_devs
        self.acceptable_re_runs = benchmarker.pytest_config.re_runs

    def collect(self):
        self.add_marker(pytest.mark.flaky(reruns=self.acceptable_re_runs))
        test_model = self.model.parse_file(self.benchmark_dir / "benchmark.json")
        for func_name, test in test_model.tests:
            for i, data in enumerate(test):
                yield JSONItem.from_parent(
                    self,
                    name=f"{func_name}{i}",
                    func_name=func_name,
                    data=data,
                    benchmarker=self.benchmarker,
                    acceptable_st_devs=self.acceptable_st_devs,
                )


def get_benchmarker_from_definition(file_path: Path) -> AutoBenchmarker:
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("autobenchmarker", file_path)
    assert spec is not None
    autobench = importlib.util.module_from_spec(spec)
    sys.modules["autobenchmarker"] = autobench
    assert spec.loader is not None
    spec.loader.exec_module(autobench)
    # TODO: check if name is correct, fail nicely
    if not isinstance(autobench.trust_random, AutoBenchmarker):
        raise ValueError("Benchmarker of incorrect type")
    return autobench.trust_random


def find_benchmarks(start_path: Path) -> Iterator[tuple[AutoBenchmarker, Path]]:
    for f in start_path.glob("benchmark_test_*.py"):
        yield get_benchmarker_from_definition(f), f


def get_benchmark_dir(start_path: Path, auto_benchmarker: AutoBenchmarker) -> Path:
    # Use either defined path or a directory of the same name as the
    # benchmark definition file
    pytest_config = auto_benchmarker.pytest_config
    return start_path / pytest_config.benchmark_path


def pytest_sessionstart(session: pytest.Session):
    for auto_benchmarker, path in find_benchmarks(session.startpath):
        benchmark_dir = get_benchmark_dir(session.startpath, auto_benchmarker)

        if not benchmark_dir.exists() or session.config.option.genbenchmark:
            auto_benchmarker.generate_benchmark(verbose=True)
        else:
            benchmark_sub_path = benchmark_dir / "benchmark.json"
            if not benchmark_sub_path.exists():
                auto_benchmarker.generate_benchmark(verbose=True)


def pytest_collect_file(parent: pytest.Session, file_path: Path):
    regex = r"benchmark_test_(.+).py"
    if m := re.match(regex, file_path.name):
        # TODO: let it through if there's no actual benchmark there - maybe just a similar name
        auto_benchmarker = get_benchmarker_from_definition(file_path)
        assert auto_benchmarker is not None
        return JSONFile.from_parent(
            parent,
            path=file_path,
            model=auto_benchmarker.test_model,
            benchmarker=auto_benchmarker,
            benchmark_dir=get_benchmark_dir(parent.startpath, auto_benchmarker),
        )


def pytest_addoption(parser):
    parser.addoption(
        "--generatebenchmark",
        dest="genbenchmark",
        action="store_true",
        help="Should (re)generate benchmark?",
    )
