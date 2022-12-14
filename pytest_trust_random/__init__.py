
import pytest
from pydantic import BaseModel
from pathlib import Path

class ExampleSubmodel(BaseModel):
    pop: int

class ExampleModel(BaseModel):
    tests: list[ExampleSubmodel]

class JSONItem(pytest.Item):
    def __init__(self, *, spec: ExampleSubmodel, **kwargs):
        super().__init__(**kwargs)
        self.spec = spec

    def runtest(self):
        assert self.spec.pop >=1

class JSONFile(pytest.File):
    def collect(self):
        raw_p = ExampleModel.parse_file(self.path)
        return [JSONItem.from_parent(self, name=f"test{i}", spec = item) for i, item in enumerate(raw_p.tests)]
 
def get_benchmarker_from_definition(file_path):
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("autobenchmarker", file_path)
    assert spec is not None
    autobench = importlib.util.module_from_spec(spec)
    sys.modules["autobenchmarker"] = autobench
    assert spec.loader is not None
    spec.loader.exec_module(autobench)

    return autobench.trust_random

def pytest_collectstart(collector: pytest.Session):
    print(collector.path)



def pytest_collect_file(parent: pytest.Session, file_path: Path):
    if file_path.suffix == ".json":
        return JSONFile.from_parent(parent, path=file_path)
    elif file_path.name == "benchmark_definition.py":
        # parent.config is accessible - take note

        trust_random = get_benchmarker_from_definition(file_path)
        #trust_random.test_result()
        #raise NotImplementedError()

