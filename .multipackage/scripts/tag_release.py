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
    parser.add_argument('-f', '--force', action="store_true",
                        help="Don't do any pre-release sanity checks")
    parser.add_argument("name", help="The name of the component that you want to release")
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=VERSION))

    return parser


def run_in_component(path, args, stdin=None):
    """Run a command in a given directory."""

    curr = os.getcwd()

    try:
        os.chdir(path)

        if stdin is not None and not isinstance(stdin, bytes):
            stdin = stdin.encode('utf-8')

        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, _stderr = proc.communicate(stdin)

        if proc.returncode != 0:
            raise GenericError("Subcommand '%s' returned a nonzero status code: %d" % (" ".join(args), proc.returncode))

        if not isinstance(stdout, str):
            stdout = stdout.decode('utf-8')

        return stdout
    finally:
        os.chdir(curr)


def verify_git_clean(path):
    """Verify that there is a nothing pending on git."""

    sys.stdout.write(" - Checking for uncommitted changes:")
    result = run_in_component(path, ['git', 'status', '--porcelain=v1'])

    lines = [x for x in result.splitlines() if len(x) > 0]

    if len(lines) == 0:
        print(" OKAY")
        return

    print(" FAILED")

    raise GenericError("There are uncommitted changes in the component, please commit or stash them")


def verify_branch(path, expected_branch="master"):
    """Verify that the branch is correct."""

    sys.stdout.write(" - Verifying your branch is %s:" % expected_branch)
    branch = run_in_component(path, ['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    branch = branch.strip()

    if branch == expected_branch:
        print(" OKAY")
        return

    print(" FAILED")

    raise GenericError("You must be on branch %s to release, you are on %s" % (expected_branch, branch))


def verify_up_to_date(path, branch="master"):
    """Verify that your branch is up to date with the remote."""

    sys.stdout.write(" - Verifying your branch up to date:")
    run_in_component(path, ['git', 'remote', 'update'])

    result = run_in_component(path, ['git', 'rev-list', 'HEAD...origin/%s' % branch, '--count'])
    count = int(result.strip())

    if count == 0:
        print(" OKAY")
        return

    print(" FAILED")

    raise GenericError("You branch is not up-to-date with remote branch: %d different commits" % count)


def create_tag(path, name, version, notes, test=False):
    """Create an annotated release tag."""

    tag_name = "{}-{}".format(name, version)
    tag_contents = "Release %s for %s\n\n%s" % (version, name, notes)

    if test:
        tag_name = "test@" + tag_name
        tag_contents = "Test " + tag_contents

    print("Creating annotated release tag: %s" % tag_name)
    run_in_component(path, ['git', 'tag', '-a', '-F', '-', tag_name], stdin=tag_contents)


def push_tag(path):
    """Push tags."""

    print("Pushing tags to remote\n")
    run_in_component(path, ['git', 'push', '--tags'])


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
        val = input("Are you sure [y/N]? ")
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

        if not args.force:
            print("\nRunning pre-release sanity checks:")
            verify_git_clean(path)
            verify_branch(path, "master")
            verify_up_to_date(path, "master")

            print()
        else:
            print('\nSkipping pre-release checks becaus -f/--force was passed\n')

        create_tag(path, comp['name'], version, release_notes)

        if args.push:
            push_tag(path)

    except (MismatchError, InternalError, ExternalError, KeyboardInterrupt, GenericError) as exc:
        retval = handle_exception(exc)

    return retval


if __name__ == "__main__":
    sys.exit(main())