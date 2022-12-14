from setuptools import setup

setup(
    name="pytest-trust-random",
    packages=["pytest_trust_random"],
    entry_points={"pytest11": ["pytest_trust_random = pytest_trust_random"]},
    classifiers=["Framework :: Pytest"],
)
