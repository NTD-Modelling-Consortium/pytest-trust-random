from setuptools import setup

setup(
    name="pytest-trust-random",
    packages=["pytest_trust_random"],
    entry_points={"pytest11": ["trustrandom = pytest_trust_random.plugin"]},
    classifiers=["Framework :: Pytest"],
)
