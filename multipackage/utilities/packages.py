"""Utilities for finding python packages."""

import os
import platform
from setuptools import find_packages


def find_toplevel_packages(path, exclude=("test",), prefix=None):
    """Find all top level python packages in the given directory.

    This will automatically exclude all subpackages and only
    report the top level package.  If you pass a prefix argument,
    then only the top level packages under that prefix will be
    reported.

    So, if you have a package hierarchy like:

    multipackage.core
    multipackage.plugins
    other_package.hello

    and you pass prefix="multipackage", then you will get
    multipackage.core
    multipackage.plugins

    Otherwise you will get:
    multipackage
    other_package

    Args:
        path (str): The path to the directory in which to search
        exclude (list of str): Exclude the given packages
        prefix (str): Optional package prefix to search under.
            If this is not None then it must not end with a .
            and will be used to find the next level of packages
            under a given prefix.

    Returns:
        list of str: The list of top level packages.
    """

    path = os.path.normpath(path)

    if os.pathsep == "\\":
        path = path.replace("\\", "/")

    packages = find_packages(path, exclude=exclude)

    if prefix is None:
        toplevel = set(x.split('.')[0] for x in packages)
    else:
        prefix_dots = prefix.count('.')
        if prefix.endswith('.'):
            prefix_dots -= 1
            prefix = prefix + '.'

        toplevel = [x for x in packages if x.startswith(prefix) and x.count('.') == prefix_dots + 1]

    return sorted(list(toplevel))
