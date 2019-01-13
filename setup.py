from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='watchcode',
    install_requires=requirements,
    #setup_requires=requirements,
    tests_require=[
        "pytest",
        "pytest-cov"
    ],
    #entry_points={
    #    'console_scripts': [
    #        'watchcode = watchcode.watchcode:main',
    #    ],
    #},
)