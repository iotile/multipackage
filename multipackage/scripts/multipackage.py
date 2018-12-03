"""Main entry point for multipackage console script."""

from __future__ import unicode_literals, absolute_import, print_function
import argparse
import sys
import os
import logging
from multipackage import Repository
from multipackage.external import TravisCI
from multipackage.exceptions import InvalidEnvironmentError, UsageError
from multipackage.utilities import GITRepository, render_template


DESCRIPTION = \
"""Manage the build, test and release scripts of a multipackage python repo.

This command line tool installs and updates a set of scripts that automate the
testing and release process of a repository hosted on GitHub and tested on
Travis CI.  It specializes in repositories that host multiple related python
packages that are released separately to PyPI.

The major things you can do are:

$ multipackage init [path to repo, default cwd]

    Provision an initial set of scripts into the repository at the given
    path or the CWD if path is not specified.

$ multipackage update [path to repo, default cwd]

    Update the build and release scripts in the given repository to the
    latest version included with this multipackage program.

$ multipackage doctor [path to repo, default cwd]

    Verify that all of your environment variables are set correctly for
    running init or update on a repository.

$ multipackage info [path to repo, default cwd]

    Get information on the packages inside the given repository.  The
    reposository must already have a working set of multipackage release
    scripts installed via a previous call to multipackage init.

    This will also verify that all of the multipackage build/release scripts
    in the given repository are correctly installed and check for common
    errors.
"""

def _variable_status(value, declarations):
    """Check that an environment variable exists."""

    required = False
    for decl in declarations:
        if decl.required:
            required = True
            break

    if value is not None:
        return "PRESENT"

    if required and value is None:
        return "MISSING"

    return "NOT PRESENT"


def doctor_repo(repo_path):
    """Verify that all required environment settings are correct."""

    repo = create_repo(repo_path)

    if repo_path is None:
        repo_path = ""

    try:
        GITRepository(repo_path)
    except UsageError:
        print("STATUS: Repository is not a valid git repo.\n")
        print("Make sure your path is correct.\n")
        return 2

    if repo.initialized is False:
        print("\nSTATUS: Repository has not been set up with multipackage.\n")
        print("Set it up with:\n\n\tmultipackage init {}\n".format(repo_path))
        return 1

    variables = {
        "repo": repo,
        "repo_path": repo_path
    }

    filters = {
        "variable_status": _variable_status
    }

    info = render_template(repo.template.DOCTOR_TEMPLATE, variables, filters=filters)
    sys.stdout.write(info)

    return 0


def create_repo(repo_path):
    """Helper method to create a Repository object."""

    if repo_path is None:
        repo_path = os.getcwd()

    return Repository(repo_path)


def init_repo(repo_path, clean):
    """Initialize or reinitialize a repository."""

    repo = create_repo(repo_path)
    repo.initialize(clean=clean)

    return 0

def update_repo(repo_path):
    """Update the installed files in a repository."""

    repo = create_repo(repo_path)

    if repo.initialized is False:
        print("\nSTATUS: Repository has not been set up with multipackage.\n")
        print("Set it up with:\n\n\tmultipackage init {}\n".format(repo_path))
        return 1

    if not repo.clean:
        print("ERROR: Repository has errors, please correct them first\n")
        print("    multipackage info {}".format(repo_path))
        return 2

    repo.update()
    return 0


def info_repo(repo_path):
    """Get info on the given repository.

    Args:
        repo_path (str): The path to the repository.

    Returns:
        int: An error code indicating any issues.
    """

    repo = create_repo(repo_path)

    if repo_path is None:
        repo_path = ""

    try:
        GITRepository(repo_path)
    except UsageError:
        print("STATUS: Repository is not a valid git repo.\n")
        print("Make sure your path is correct.\n")
        return 2

    if repo.initialized is False:
        print("\nSTATUS: Repository has not been set up with multipackage.\n")
        print("Set it up with:\n\n\tmultipackage init {}\n".format(repo_path))
        return 1

    repo.manifest.verify_all(report=True)

    variables = {
        "repo": repo,
        "repo_path": repo_path
    }

    info = render_template(repo.template.INFO_TEMPLATE, variables)
    sys.stdout.write(info)

    if not repo.clean:
        return 1

    return 0


def build_parser():
    """Build the argument parser."""
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--verbose', action="count", default=0, help="Increase logging level (goes error, warn, info, debug)")
    subparser = parser.add_subparsers(title="Supported Subcommands", dest='action')

    init_parser = subparser.add_parser('init', description="Initialize or forcibly clean and reinitialize a repository.",
                                       help='initialize (or clean and reinitialize) a repo')
    init_parser.add_argument('-f', '--force', action="store_true", help="Forcibly clean and reinitialize the repo")
    init_parser.add_argument('repo', nargs='?', help="Optional path to repository, defaults to cwd")

    doctor_parser = subparser.add_parser('doctor', description="Verify your environment settings and connectivity.",
                                         help='verify your enviornment for multipackage usage')
    doctor_parser.add_argument('repo', nargs='?', help="Optional path to repository, defaults to cwd")

    info_parser = subparser.add_parser('info', description="Get info on the given repository and verify it is correctly installed",
                                       help="get info and any errors with a repository")
    info_parser.add_argument('repo', nargs='?', help="Optional path to repository, defaults to cwd")

    update_parser = subparser.add_parser('update', description="Update all managed files to their latest versions",
                                         help="update all managed files to their latest versions")
    update_parser.add_argument('repo', nargs='?', help="Optional path to repository, defaults to cwd")

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


def print_usage_error(err):
    """Print an error about incorrect usage."""

    print("USAGE ERROR: %s" % err.message)

    if err.suggestion is not None:
        print("Suggestion: %s" % err.suggestion)


def main(argv=None):
    """Main entry point for multipackage console script."""

    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()

    args = parser.parse_args(argv)
    setup_logging(args)

    retval = 0

    try:
        if args.action == 'doctor':
            retval = doctor_repo(args.repo)
        elif args.action == 'info':
            retval = info_repo(args.repo)
        elif args.action == "init":
            retval = init_repo(args.repo, args.force)
        elif args.action == "update":
            retval = update_repo(args.repo)
        else:
            print("ERROR: Command Not Supported Yet")
            retval = 1
    except UsageError as err:
        print_usage_error(err)
        retval = 1
    except InvalidEnvironmentError as err:
        print_environment_error(err)
        retval = 1
    except:
        raise

    return retval

