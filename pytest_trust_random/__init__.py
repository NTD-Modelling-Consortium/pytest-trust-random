"""**pytest-trust-rundom** is a [pytest](https://docs.pytest.org/en/latest/contents.html)
plugin. It designed to facilitate regression testing of randomised (although not only)
functions over the whole spectrum of defined parameters.

In order to use it, you must define an object of `PytestConfig` class and then
use it to create pytest-trust-random tests.

Files with the tests need to match the following pattern: `benchmark_test_*.py`
For example: benchmark_test_simulation.py

Basic usage:
    ```py
    # tests/benchmark_test_simulation.py
    from pytest_trust_random import benchmark_test, PytestConfig
    
    cfg = PytestConfig(acceptable_st_devs=2.5, re_runs=5, benchmark_path="benchmarks")
    class Stats:
        some_output_data: float
    
    @benchmark_test
    def test_simulation_1(a: int, b: float) -> Stats:
        ...
        return Stats(...)
    
    @benchmark_test
    def test_simulation_2(a: int, b: float) -> Stats:
        ...
        return Stats(...)
    ```
    
    Now, run `pytest -s`. If benchmarks and settings files were not created earlier,
    the plugin will prompt you (hence `-s` is important) to provide the following:
    Then it will create a benchmark.json file in the specified `benchmark_path` for all
    the tests defined.

    The following runs of `pytest` do not require `-s` argument, as they won't prompt
    for any user input.
"""

__all__ = ["benchmark_test", "PytestConfig"]

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

FILE_NAME_PATTERN = re.compile(r"benchmark_test_.+.py")


def is_auto_benchmarker_test_file(path: Path) -> bool:
    return re.match(FILE_NAME_PATTERN, path.name) is not None


def benchmark_test(pytest_config: PytestConfig):
    """Decorator for creating benchmark tests from functions.

    The plugin will create tests combination of function parameters.
    Maximum, minimum, number of steps for each of them as well as maximum
    product of the parameters will be prompted by the plugin when run for the first time.

    Examples:
        >>> config = PytestConfig(...)
        >>> @benchmark_test(config)
        ... def test_something(a: int, b: float, c: int):
        ...     ...

    Args:
        pytest_config (PytestConfig): Test configuration
    """

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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.benchmarkers = benchmarkers

    def collect(self):
        for benchmarker in self.benchmarkers:
            pytest_config = benchmarker.pytest_config
            model = benchmarker.test_model

            test_model = model.parse_file(benchmarker.benchmark_file_path)
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
    for f in filter(is_auto_benchmarker_test_file, start_path.iterdir()):
        yield from get_benchmarkers_from_definition(f)


def get_benchmark_dir(start_path: Path, auto_benchmarker: AutoBenchmarker) -> Path:
    pytest_config = auto_benchmarker.pytest_config
    # TODO: is this start_path needed?
    return start_path / pytest_config.benchmark_path


def pytest_sessionstart(session: pytest.Session):
    for auto_benchmarker in find_benchmarks(session.startpath):
        benchmark_dir = get_benchmark_dir(session.startpath, auto_benchmarker)

        if not benchmark_dir.exists() or session.config.option.genbenchmark:
            auto_benchmarker.generate_benchmark(verbose=True)
        else:
            if not auto_benchmarker.benchmark_file_path.exists():
                auto_benchmarker.generate_benchmark(verbose=True)


def pytest_collect_file(parent: pytest.Session, file_path: Path):
    if is_auto_benchmarker_test_file(file_path):
        # TODO: let it through if there's no actual benchmark there - maybe just a similar name
        auto_benchmarkers = get_benchmarkers_from_definition(file_path)
        return JSONFile.from_parent(
            parent,
            path=file_path,
            benchmarkers=auto_benchmarkers,
        )


def pytest_addoption(parser):
    parser.addoption(
        "--generatebenchmark",
        dest="genbenchmark",
        action="store_true",
        help="Should (re)generate benchmark?",
    )
