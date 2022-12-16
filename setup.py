from setuptools import setup

setup(
    name="pytest-trust-random",
    entry_points={"pytest11": ["name_of_plugin = pytest_trust_random"]},
    classifiers=["Framework :: Pytest"],
    version="0.1.0",
    packages=["pytest_trust_random"],
)
