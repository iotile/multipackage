"""Single script finds and releases a component by name."""

from __future__ import print_function
import sys
import os
import subprocess

from components import COMPONENTS


def main():
    """Main entry point to test_by_name.py."""

    if len(sys.argv) != 2:
        print("Usage: test_by_name.py <component>")
        return 1

    name = sys.argv[1]

    if name not in COMPONENTS:
        print("ERROR: Could not find component %s to test\nKnown components: %s" % (name, ", ".join(COMPONENTS)))
        return 1

    comp = COMPONENTS[name]

    print()
    print("Testing component %s" % name)
    print()

    cwd = os.getcwd()

    try:
        os.chdir(comp['path'])
        retval = subprocess.call(['pytest', 'test'])
    finally:
        os.chdir(cwd)

    return retval

if __name__ == '__main__':
    sys.exit(main())