
from typing import Optional, Type
import pytest
from pydantic import BaseModel
from pathlib import Path
from .definitions.auto_benchmarker import AutoBenchmarker
from .definitions.pytest_config import PytestConfig

class ExampleSubmodel(BaseModel):
    pop: int

class ExampleModel(BaseModel):
    tests: list[ExampleSubmodel]

class JSONItem(pytest.Item):
    def __init__(self, *, spec: ExampleSubmodel, **kwargs):
        super().__init__(**kwargs)
        self.spec = spec

    def runtest(self):
        print(self.spec)
        assert self.spec.pop >=1

class JSONFile(pytest.File):
    def __init__(self, *, model: Type[BaseModel], **kwargs):
        super().__init__(**kwargs)
        self.model = model
    def collect(self):
        raw_p = self.model.parse_file(self.path)
        final_tests = []
        for name, test in raw_p.tests:
            final_tests += [JSONItem.from_parent(self, name=f"{name}{i}", spec = x) for i, x in enumerate(test)]
        return final_tests
 
def get_benchmarker_from_definition(file_path) -> AutoBenchmarker:
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("autobenchmarker", file_path)
    assert spec is not None
    autobench = importlib.util.module_from_spec(spec)
    sys.modules["autobenchmarker"] = autobench
    assert spec.loader is not None
    spec.loader.exec_module(autobench)
    if not isinstance(autobench.trust_random, AutoBenchmarker):
        raise ValueError('Benchmarker of incorrect type')
    return autobench.trust_random

def get_benchmarker_from_startpath(start_path) -> Optional[AutoBenchmarker]:
    # Generate benchmark from definition and settings
    definition_path = Path(str(start_path) + '/' + 'benchmark_definition.py')
    if not definition_path.exists():
        return None
    auto_benchmarker = get_benchmarker_from_definition(definition_path)
    return auto_benchmarker

def get_pytest_config_from_startpath(start_path) -> Optional[PytestConfig]:
    config_path = Path(str(start_path) + '/' + 'pytest_config.json')
    if config_path.exists():
        return PytestConfig.parse_file(config_path)
    else:
        return None

def pytest_sessionstart(session: pytest.Session):
    pytest_config = get_pytest_config_from_startpath(session.startpath)
    auto_benchmarker = get_benchmarker_from_startpath(session.startpath)
    if not auto_benchmarker or not pytest_config:
        raise ValueError('benchmark or pytest_config not found')
    benchmark_path = Path(str(session.startpath) + '/' + pytest_config.benchmark_path)

    # get addoption from collector and generate if specified
    if not benchmark_path.exists():
        auto_benchmarker.generate_benchmark()
    else:
        benchmark_sub_path = Path(str(benchmark_path) + '/' + 'benchmark.json')
        if not benchmark_sub_path.exists():
            auto_benchmarker.generate_benchmark()




def pytest_collect_file(parent: pytest.Session, file_path: Path):
    if file_path.name == "benchmark.json":
        auto_benchmarker = get_benchmarker_from_startpath(parent.startpath)
        assert auto_benchmarker is not None
        return JSONFile.from_parent(parent, path=file_path, model = auto_benchmarker.test_model)


def pytest_addoption(parser):
    parser.addoption(
        "--generatebenchmark",
        dest="genbenchmark",
        action="store_true",
        help="my option: type1 or type2",
    )
