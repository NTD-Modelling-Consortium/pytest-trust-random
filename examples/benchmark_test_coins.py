import numpy as np
import pydantic

from pytest_trust_random import TrustRandomConfig, benchmark_test


class CoinTosserStats(pydantic.BaseModel):
    no_of_heads: int


config = TrustRandomConfig(
    acceptable_st_devs=1.5,
    re_runs=5,
    benchmark_path="benchmark",
)


@benchmark_test(config)
def coin_tosser(n: int) -> CoinTosserStats:
    heads = np.random.binomial(n, 0.5)
    return CoinTosserStats(no_of_heads=heads)


class BinomialOutcome(pydantic.BaseModel):
    no_of_successes: int


@benchmark_test(config)
def binomial(n: int, p: float) -> BinomialOutcome:
    outcome = np.random.binomial(n, p)
    return BinomialOutcome(no_of_successes=outcome)
