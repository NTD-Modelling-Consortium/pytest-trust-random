from pydantic import BaseModel
from pytest_trust_random import AutoBenchmarker

class Stats(BaseModel):
    pop: int

def tiny_test(pop: int, other: int) -> Stats:
    return Stats(pop = pop)

trust_random = AutoBenchmarker(tiny_test = tiny_test)
