"""Utilities for finding python packages."""

import os
import platform
from setuptools import find_packages


def find_toplevel_packages(path, exclude=("test",)):
    """Find all top level python packages in the given directory.

    This will automatically exclude all subpackages and only
    report the top level package.

    Args:
        path (str): The path to the directory in which to search
        exclude (list of str): Exclude the given packages

    Returns:
        list of str: The list of top level packages.
    """

    path = os.path.normpath(path)

    if os.pathsep == "\\":
        path = path.replace("\\", "/")

    packages = find_packages(path, exclude=exclude)

    toplevel = set(x.split('.')[0] for x in packages)
    return sorted(list(toplevel))
