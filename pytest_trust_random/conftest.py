import pytest
from pydantic import BaseModel

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
 

def pytest_collect_file(parent, file_path):
    if file_path.suffix == ".json":
        return JSONFile.from_parent(parent, path=file_path)
