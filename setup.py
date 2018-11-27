"""Setup file for multipackage."""

from setuptools import setup, find_packages
from version import version

setup(
    name="multipackage",
    packages=find_packages(exclude=("test",)),
    version=version,
    license="LGPLv3",
    install_requires=[
        "cookiecutter",
        "pycryptodome",
        "requests",
        "pyyaml"
    ],
    include_package_data=True,
    entry_points={
        "console_scripts": ['multipackage = multipackage.scripts.multipackage:main']
    },
    description="A CLI tool for managing CI and CD scripts on multi-package repositories",
    author="Arch Systems",
    author_email="info@archsys.io",
    url="https://github.com/iotile/python_multipackage",
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
Multipackage
------------

<TODO>
"""
)
