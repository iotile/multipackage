"""Helper script to tag a release by name."""

from __future__ import print_function
import os
import sys
import argparse
import subprocess

if sys.version_info.major < 3:
    from builtins import raw_input as input

from components import COMPONENTS  #pylint:disable=import-error; This is a templated file that is copied into place
from release_notes import get_release_notes, get_version  #pylint:disable=import-error; This is a templated file that is copied into place
from shared_errors import MismatchError, ExternalError, InternalError, GenericError, handle_exception  #pylint:disable=import-error; This is a templated file that is copied into place



VERSION = "0.1.0"

def build_parser():
    """Build argument parser."""

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--no-push", dest="push", action="store_false",
                        help="Do not automatically push to the tag to origin")
    parser.add_argument("-y", "--yes", dest="confirm", action="store_false",
                        help="Do not prompt for confimation")
    parser.add_argument("-t", "--test", action="store_true",
                        help="Create a test release tag that will trigger a dry-run")
    parser.add_argument("name", help="The name of the component that you want to release")
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=VERSION))

    return parser


def run_in_component(path, args):
    curr = os.getcwd()

    try:
        os.chdir(path)

        result = subprocess.check_output(args)
        if not isinstance(result, str):
            result = result.decode('utf-8')

        return result
    finally:
        os.chdir(curr)


def verify_git_clean(path):
    """Verify that there is a nothing pending on git."""

    result = run_in_component(path, ['git', 'status', '--porcelain=v1'])
    print(result)    


def show_confirm_version(name, version, release_notes, confirm, will_push, test):
    """Print and optionally confirm the release action."""

    print()
    print("Name: %s" % name)
    print("Version: %s" % version)
    print()

    print("Release Notes")
    print(release_notes)

    print()

    if will_push:
        print("Saying yes will automatically push the tag to `origin`, triggering the release immediately")
    else:
        print("The tag **will not** be pushed automatically, you will need to call `git push --tags` yourself")

    if test:
        print()
        print("**This will be a dry-run that will not actually release anything permanently.**")

    print()

    if confirm:
        val = input("Are you sure [y/N]?")
        if val.lower() != 'y':
            raise GenericError("Cancelled by user", 100)


def main():
    """Main entry point to tag_release.py."""

    parser = build_parser()
    args = parser.parse_args()

    retval = 0
    try:
        comp = COMPONENTS.get(args.name)
        if comp is None:
            raise MismatchError("component name", "one of " + ", ".join(COMPONENTS), args.name)

        path = comp['path']
        version = get_version(path)
        release_notes = get_release_notes(path, version)

        show_confirm_version(args.name, version, release_notes, args.confirm, args.push, args.test)

        verify_git_clean(path)

    except (MismatchError, InternalError, ExternalError, KeyboardInterrupt, GenericError) as exc:
        retval = handle_exception(exc)

    return retval


if __name__ == "__main__":
    sys.exit(main())
