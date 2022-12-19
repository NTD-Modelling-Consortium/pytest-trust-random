from typing import Dict, Generic, List, TypeVar, Union

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, root_validator
from pydantic.generics import GenericModel


class BenchmarkArray(BaseModel):
    mean: float
    st_dev: float

    @classmethod
    def from_array(cls, array: Union[NDArray[np.float_], NDArray[np.int_]]):
        return cls(mean=float(np.mean(array)), st_dev=float(np.std(array)))


class BaseSettingsModel(BaseModel):
    """
    The settings corresponding to one function
    """

    max_product: float
    benchmark_iters: int


class GlobalSettingsModel(BaseModel):
    """
    The settings corresponding to all functions
    """


class BaseOutputData(BaseModel):
    data: Dict[str, BenchmarkArray]


DataT = TypeVar("DataT")


class BaseTestDimension(GenericModel, Generic[DataT]):
    minimum: DataT
    maximum: DataT
    steps: int

    @root_validator
    def check_max_not_greater_than_min(cls, values):
        if values.get("maximum") < values.get("minimum"):
            raise ValueError("Minimum is greater than maximum")
        return values


TestT = TypeVar("TestT", bound=BaseOutputData)


class BaseTestModel(GenericModel, Generic[TestT]):
    tests: List[TestT]


class PytestConfig(BaseModel):
    acceptable_st_devs: float
    re_runs: int
    benchmark_path: str

    def __hash__(self) -> int:
        return hash(self.benchmark_path)
