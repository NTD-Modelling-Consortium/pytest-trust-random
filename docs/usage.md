## Installation

**pytest-trust-random** is compatible with python 3.10 and newer.

In order to use **pytest-trust-random** you need to add it to your project's dependencies.
It will work either with `poetry` or `pip`. It should also work with other python package managers.

If you use `poetry`, run:

```bash
poetry add git+https://github.com/dreamingspires/pytest-trust-random
```

If you use `pip`, run:

```bash
pip install git+https://github.com/dreamingspires/pytest-trust-random
```

Both commands will install all the necessary packages required by **pytest-trust-random** including **pytest** and **pydantic** if you don't have it installed already.

## Create a first test

In order to create your first test with **pytest-trust-random**, create a file following this pattern: `benchmark_test_*.py`. In our example,
we'll create a file `benchmark_test_coins.py`.

The function you are testing should take at least one parameter and return an object which is a **pydantic** model (i.e. its class must inherit from `pydantic.BaseModel`).

First, let's import all the required bits

```py
import numpy as np # needed just for our function
import pydantic

from pytest_trust_random import benchmark_test, TrustRandomConfig
```

Then, create a return type for the function under test.

```py
class CoinTosserStats(pydantic.BaseModel):
    no_of_heads: int
```

Before we create our function under test, we need an instance of TrustRandomConfig. These are a set of parameters required by **pytest-trust-random**. Please check the [Reference](reference.md) for detailed explanation of the parameters.

```py
config = TrustRandomConfig(
    acceptable_st_devs=1.5,
    re_runs=5,
    benchmark_path="benchmarks",
)
```

Now, let's create our function under test

```py title="Function under test"
@benchmark_test(config)
def coin_tosser(n: int) -> CoinTosserStats:
    heads = np.random.binomial(n, 0.5)
    return CoinTosserStats(no_of_heads=heads)
```

**NOTE:** if your function under test is already defined elsewhere, you don't need to use the decorator in the way described above. Just do this instead somewhere in your test file:

```py
benchmark_test(config)(coin_tosser)
```

## Generate benchmark and settings files

Everything what's needed is done. Now it's time to generate the benchmark and settings files. These will be stored in `config.benchmark_path`, so in our example: `benchamarks/` directory.
In order to do that, you _must_ run `pytest` with `-s` option (short for `--capture=no`). This is needed because generating the benchmark and config files is interactive. Below is the example run:

```bash
$ poetry run pytest -s
Attributes for function coin_tosser:
Enter attributes for `n` (minimum: int, maximum: int, steps: int): 1,25000,10
benchmark_iters (int): 1000

Benchmark will run 10 tests
[...]

================== test session starts ==================
platform linux -- Python 3.10.6, pytest-7.2.0, pluggy-1.0.0
rootdir: [...]
plugins: rerunfailures-10.3, trust-random-0.1.0
collected 10 items

benchmark_test_coins.py .......R...

================== 10 passed in 0.08s ==================
```

A few things need an explation. Let's start with our input:

- Attributes for `n`: by typing `1,25000,10` we are saying that our `coin_tosser` will run for a `10` evently spaced values on a log scale of `n` from `1` to `25000`. So the values of `n` will be as follows in our case: `1, 3, 9, 29, 90, 378, 855, 2634, 8115, 25000`.
- Each of these runs will be executed 1000 times (`benchmark_iters` parameter) in order to get an accurate estimation of the mean and keep standard deviation low.

Now, feel free to inspect the generated `benchmarks/benchmark.json` file. For example if you look at an entry where `n` is `25000`, you'll find something similar to this:

```json
{
  "data": {
    "no_of_heads": {
      "mean": 12495.294,
      "st_dev": 81.41918425039643
    }
  },
  "n": 25000
}
```

This is the expectation for a single test, for `n=25000`. When the `coin_tosser` function is tested, the results will be compared to the values above.

Even though we run the `coin_tosser` 1000 times for each of the inputs, our test might still fall outside of the specified number of standard deviations (`config.acceptable_st_devs`). That's why, we also define how many re-runs can pytest run before the test is considered failed (`config.re_runs`). In the above listing, you can identify these attempts by `R` instead of `.`.

## Running the tests

If the settings file has already been generated, you can just run your test without pytests's `-s` flag, although feel free to use it - it won't harm. If your benchmark file hasn't been generated or has been deleted, it will automatically generate it before the tests are executed.

```bash
pytest
```

## Regenerating benchmark

If from some reason you wish to re-generate the benchmark file, you can run pytest with a `--generatebenchmark` flag. Like that:

```bash
pytest --generatebenchmark
```

## Adding more tests

There's nothing preventing us from adding more tests. You can do it either in the same file or another, either with the same `TrustRandomConfig` or with another. If you decide you tests needs a different `TrustRandomConfig`, make sure you use different `benchmark_path` for each of the configs. As an example, we'll add another function to our test file.

```py
@benchmark_test(config)
def binomial(n: int, p: float) -> BinomialOutcome:
    outcome = np.random.binomial(n, p)
    return BinomialOutcome(no_of_successes=outcome)
```

After adding the tests, we should remove the existing `benchmarks/` directory, so that the settings and benchmark itself can be regenerated.
After deleting the directory, run

```bash
$ poetry run pytest -s
Attributes for function binomial:
Enter attributes for `n` (minimum: int, maximum: int, steps: int): 1,1000,10
Enter attributes for `p` (minimum: float, maximum: float, steps: int): 0.1,0.9,10
max_product (float): 500
benchmark_iters (int): 1000

Attributes for function coin_tosser:
Enter attributes for `n` (minimum: int, maximum: int, steps: int): 1,25000,10
benchmark_iters (int): 10000

[...]

================== test session starts ==================
platform linux -- Python 3.10.6, pytest-7.2.0, pluggy-1.0.0
rootdir: [...]
plugins: rerunfailures-10.3, trust-random-0.1.0
collected 107 items

benchmark_test_coins.py ................R.........R............R............R..............R.....R...............................R..R......

================== 107 passed, 8 rerun in 0.38s ==================
```

The above will result in a generated benchmark for 107 different tests. 10 of which will test `coin_tosser` as per the first example. The rest will be the tests for `binomial` function, for multiple different values of `n` and `p`, as specified. `max_product` is a limit of multiplication of all of the parameters. That means that for instance, a test for `n=1000, p=0.9` will not be generated, because the product of `n*p` exceeds specified value of 500.
