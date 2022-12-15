# -*- coding: utf-8 -*-
from setuptools import setup

packages = ["pytest_trust_random"]

package_data = {"": ["*"]}

install_requires = [
    "joblib>=1.2.0,<2.0.0",
    "numpy>=1.23.5,<2.0.0",
    "pydantic>=1.10.2,<2.0.0",
    "pytest-rerunfailures>=10.3,<11.0",
    "pytest>=7.2.0,<8.0.0",
]

setup_kwargs = {
    "name": "pytest-trust-random",
    "version": "0.1.0",
    "description": "",
    "long_description": None,
    "author": "mark-todd",
    "author_email": "markpeter.todd@hotmail.co.uk",
    "maintainer": None,
    "maintainer_email": None,
    "url": None,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "python_requires": ">=3.10,<3.11",
    "entry_points": {"pytest11": ["trustrandom = pytest_trust_random.plugin"]},
    "classifiers": ["Framework :: Pytest"],
}

setup(**setup_kwargs)
