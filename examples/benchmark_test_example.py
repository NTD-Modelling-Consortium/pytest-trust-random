from pydantic import BaseModel

from pytest_trust_random import benchmark_test
from pytest_trust_random.base_models import PytestConfig


class Stats(BaseModel):
    pop: int


pytest_config_1 = PytestConfig(
    acceptable_st_devs=2.5,
    re_runs=5,
    benchmark_path=f"benchmarks/benchmark_test_example.py.cfg1",
)

pytest_config_2 = PytestConfig(
    acceptable_st_devs=1.5,
    re_runs=10,
    benchmark_path=f"benchmarks/benchmark_test_example.py.cfg2",
)


@benchmark_test(pytest_config_1)
def tiny_test1(pop: int, other: int) -> Stats:
    return Stats(pop=pop)


@benchmark_test(pytest_config_1)
def tiny_test2(pop: int, other: int) -> Stats:
    return Stats(pop=pop)


@benchmark_test(pytest_config_2)
def tiny_test3(pop: int, other: int) -> Stats:
    return Stats(pop=pop)
