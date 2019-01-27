from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="watchcode",
    version="0.1.0",
    description="Generic tool to solve the modify + re-run problem",
    install_requires=requirements,
    tests_require=[
        "pytest",
        "pytest-cov",
    ],
    py_modules=['watchcode'],
    license="MIT",
    author="Fabian Keller",
)