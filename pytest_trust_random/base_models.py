from typing import Generic, TypeVar

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, root_validator
from pydantic.generics import GenericModel


class BenchmarkArray(BaseModel):
    mean: float
    st_dev: float

    @classmethod
    def from_array(cls, array: NDArray[np.float_] | NDArray[np.int_]):
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
    data: dict[str, BenchmarkArray]


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
    tests: list[TestT]


class TrustRandomConfig(BaseModel):
    """Parameters specification for a single group of pytest-trust-random tests

    Attributes:
        acceptable_st_devs (int): Acceptable standard deviation
        re_runs (int): Maximum number of re-runs before a test is considered failed
        benchmark_path (str): Relative path of a directory where both settings and
                              generated benchmark files are stored
    """

    acceptable_st_devs: float
    re_runs: int
    benchmark_path: str

    def __hash__(self) -> int:
        """Hash method -- based on `benchmark_path`

        Used for deferentiating between different TrustRandomConfigs and grouping
        tests using the same config together.

        Returns:
            int: hash value
        """
        return hash(self.benchmark_path)
