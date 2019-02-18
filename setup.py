from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="watchcode",
    version="0.1.0",
    description="Generic tool to solve the modify + re-run problem",
    install_requires=requirements,
    setup_requires=["pytest-runner"],
    tests_require=[
        "pytest",
        "pytest-cov",
    ],
    packages=find_packages(),
    license="MIT",
    author="Fabian Keller",
    package_data={"": ["**/*.yaml", "**/*.wav"]},
    include_package_data=True,
)