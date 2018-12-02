"""Setup file for multipackage."""

from setuptools import setup, find_packages
from version import version

setup(
    name="iotile-analytics-offline",
    packages=find_packages(exclude=("test",)),
    version=version,
    license="LGPLv3",
    description="A demo project for integration testing",
    author="Arch Systems",
    author_email="info@archsys.io",
    url="https://github.com/iotile/iotile_analytics",
    keywords=[""],
    classifiers=[
        "Programming Language :: Python",
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules"
        ],
    long_description="""\
iotile-analytics-offline
------------------------

"""
)
