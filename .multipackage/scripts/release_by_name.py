"""Single script finds and releases a component by name."""

from __future__ import print_function
import sys
import os
import subprocess

from components import COMPONENTS


def main():
    """Main entry point to release_by_name.py."""

    if len(sys.argv) != 2:
        print("Usage: release_by_name.py <tag>")
        return 1

    tag = sys.argv[1]
    name, _, version = tag.partition('-')

    check = False
    if name.startswith('test@'):
        name = name[5:]
        check = True

    if name not in COMPONENTS:
        print("Skipping release because tag name is not known: %s" % name)
        return 0

    comp = COMPONENTS[name]
    compat = comp['options']['compatibility']

    repo = os.environ.get("PYPI_URL")
    if repo is None:
        repo = "pypi"

    slack = os.environ.get("SLACK_WEB_HOOK")

    pypi_pass = os.environ.get("PYPI_PASS")
    if pypi_pass is None:
        pypi_pass = ""

    release_script = os.path.join(".multipackage", "scripts", "release_component.py")
    args = ['python', release_script, "-e", version, "-u", os.environ.get("PYPI_USER"), '--password=%s' % pypi_pass,
            '-c', compat, "-r", repo]

    if slack is not None:
        args.extend(['-s', slack])

    if check:
        args.extend(['--check'])

    print()
    print("Invoking release_component.py with the following information")
    print("  - Slack Notification: %s" % (slack is not None))
    print("  - PyPI Index: %s" % repo)
    print("  - Component: %s" % name)
    print("  - Compatibility: %s" % compat)
    print("  - Expected Version: %s" % version)
    print("  - Dry-run: %s" % check)

    print()

    retval = subprocess.call(args)
    return retval

if __name__ == '__main__':
    sys.exit(main())