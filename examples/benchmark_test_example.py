from pydantic import BaseModel

from pytest_trust_random import AutoBenchmarker
from pytest_trust_random.base_models import PytestConfig


class Stats(BaseModel):
    pop: int


def tiny_test(pop: int, other: int) -> Stats:
    return Stats(pop=pop)


pytest_config = PytestConfig(
    acceptable_st_devs=2.5,
    re_runs=5,
    benchmark_path=f"benchmarks/benchmark_test_example.py",
)
trust_random = AutoBenchmarker(pytest_config, tiny_test=tiny_test)
