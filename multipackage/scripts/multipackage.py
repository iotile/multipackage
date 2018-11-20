"""Main entry point for multipackage console script."""

from __future__ import unicode_literals, absolute_import, print_function
import argparse
import sys
import os
import logging
from multipackage.travis import TravisCI
from multipackage.exceptions import InvalidEnvironmentError

DESCRIPTION = \
"""Manage the build, test and release scripts of a multipackage python repo.

This command line tool installs and updates a set of scripts that automate the
testing and release process of a repository hosted on GitHub and tested on
Travis CI.  It specializes in repositories that host multiple related python
packages that are released separately to PyPI.

The major things you can do are:

$ multipackage init <path to repo or cwd>

    Provision an initial set of scripts into the repository at the given
    path or the CWD if path is not specified.  The program will ask you
    a series of questions to confirm actions its taking and make sure
    everything is setup correctly.

$ multipackage update <path to repo or cwd>

    Update the build and release scripts in the given repository to the
    latest version included with this multipackage program.

$ multipackage verify <path to repo or cwd>

    Verify that all of the multipackage build/release scripts in the given
    repository are correctly installed and check for common errors.

$ multipackage doctor

    Verify that all of your environment variables are set correctly for
    running init or update on a repository.

$ multipackage info <path to repo or cwd>

    Get information on the packages inside the given repository.  The
    reposository must already have a working set of multipackage release
    scripts installed via a previous call to multipackage init.

$ multipackage release <path to repo or cwd> <package name> <version>

    Tag the given package for release.  Note that this just tags the package
    for release, it does not actually release it.  Releasing happens on Travis
    CI once the tagged commit is built and verified.  This method will check
    for and prevent common release mistakes like not being on master, not
    having fetched the latest changes, etc.
"""

def verify_environment():
    """Verify that all required environment settings are correct."""

    travis = TravisCI()
    travis.ensure_token()
    travis.get_key('iotile/typedargs')
    encoded = travis.encrypt_string('iotile/typedargs', "TEST_ENV=hello")


def build_parser():
    """Build the argument parser."""
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--verbose', action="count", default=0, help="Increase logging level (goes error, warn, info, debug)")
    subparser = parser.add_subparsers(title="Supported Subcommands", dest='action')

    init_parser = subparser.add_parser('init', description="Initialize or forcibly clean and reinitialize a repository.",
                                       help='initialize (or clean and reinitialize) a repo')
    init_parser.add_argument('-c', '--clean', action="store_true", help="Forcibly clean and reinitialize the repo")
    init_parser.add_argument('repo', nargs='?', help="Optional path to repository, defaults to cwd")

    _doctor_parser = subparser.add_parser('doctor', description="Verify your environment settings and connectivity.",
                                          help='verify your enviornment for multipackage usage')

    return parser


def setup_logging(args):
    """Setup log level and output."""

    should_log = args.verbose > 0
    verbosity = args.verbose

    root = logging.getLogger()

    if should_log:
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname).3s %(name)s %(message)s', '%y-%m-%d %H:%M:%S')
        handler = logging.StreamHandler()

        handler.setFormatter(formatter)

        loglevels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
        if verbosity >= len(loglevels):
            verbosity = len(loglevels) - 1

        level = loglevels[verbosity]

        root.setLevel(level)
        root.addHandler(handler)
    else:
        root.addHandler(logging.NullHandler())


def print_environment_error(err):
    """Print an error about a missing or incorrect ENV variable."""

    value = os.environ.get(err.variable_name)

    if value is None:
        print("ERROR: A required environment variable is not set correctly")
    else:
        print("ERROR: A required environment variable is missing")

    print("Variable Name: %s" % err.variable_name)

    if value is not None:
        print("Current Value: %s" % os.environ.get(err.variable_name))

    print("Use: %s" % err.reason)
    print("Suggestion: %s" % err.suggestion)


def main(argv=None):
    """Main entry point for multipackage console script."""

    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()

    args = parser.parse_args(argv)
    setup_logging(args)

    try:
        if args.action == 'doctor':
            verify_environment()
        else:
            print("ERROR: Command Not Supported Yet")
            return 1
    except InvalidEnvironmentError as err:
        print_environment_error(err)
        return 1
    except:
        raise

    return 0
