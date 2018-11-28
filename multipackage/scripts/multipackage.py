"""Main entry point for multipackage console script."""

from __future__ import unicode_literals, absolute_import, print_function
import argparse
import sys
import os
import logging
from multipackage import Repository
from multipackage.travis import TravisCI
from multipackage.exceptions import InvalidEnvironmentError, UsageError
from multipackage.utilities import GITRepository

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

$ multipackage doctor

    Verify that all of your environment variables are set correctly for
    running init or update on a repository.

$ multipackage info <path to repo or cwd>

    Get information on the packages inside the given repository.  The
    reposository must already have a working set of multipackage release
    scripts installed via a previous call to multipackage init.

    This will also verify that all of the multipackage build/release scripts
    in the given repository are correctly installed and check for common
    errors.

$ multipackage release <path to repo or cwd> <package name> <version>

    Tag the given package for release.  Note that this just tags the package
    for release, it does not actually release it.  Releasing happens on Travis
    CI once the tagged commit is built and verified.  This method will check
    for and prevent common release mistakes like not being on master, not
    having fetched the latest changes, etc.
"""


def verify_env_var(name, message):
    """Check that an environment variable exists."""

    if os.environ.get(name) is None:
        print("  - %s: ERROR, NOT PRESENT" % name)
        print("    Needed for %s" % message)
        return 0

    print("  - %s: OKAY" % name)
    return 1


def verify_environment():
    """Verify that all required environment settings are correct."""

    travis = TravisCI()
    travis.ensure_token()

    GITRepository.version()

    print("\nChecking for required environment variables:")

    found = 0
    found += verify_env_var("TRAVIS_TOKEN_ORG", "encrypting environment variables on travis-ci.org")
    found += verify_env_var("TRAVIS_TOKEN_COM", "encrypting environment variables on travis-ci.com")
    found += verify_env_var("GITHUB_TOKEN", "deploying documentation to github pages")
    found += verify_env_var("SLACK_TOKEN", "sending slack notifications")

    print()

    if found == 3:
        return 0

    return 1


def create_repo(repo_path):
    """Helper method to create a Repository object."""

    if repo_path is None:
        repo_path = os.getcwd()

    return Repository(repo_path)


def init_repo(repo_path, clean):
    """Initialize or reinitialize a repository."""

    repo = create_repo(repo_path)
    repo.initialize(clean=clean)


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


def verify_repo(repo_path):
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

    #FIXME: There are missing branches on this logic tree
    if repo.clean and not repo.settings_changed and len(repo.warnings) == 0:
        print("STATUS: Repository is up-to-date with no problems.\n")
    elif repo.clean and repo.settings_changed:
        print("STATUS: Repository needs to be updated.\nRUN TO UPDATE:\n\n    multipackage update {}\n".format(repo_path))
    elif repo.clean:
        print("STATUS: Repository has %d warning(s)\n" % len(repo.warnings))
    else:
        print("STATUS: Repository has %d error(s) that need to be addressed\n" % len(repo.errors))

    print("COMPONENTS:\n")
    for component in sorted(repo.components.values()):
        print("  - %s: %s\n    python-version=%s" % (component.name, component.relative_path, component.compatibility))
        print("    packages: %s" % (", ".join(component.desired_packages)))

    print()

    if len(repo.errors) > 0:
        print("ERRORS:")
        for error in repo.errors:
            print("  - {}: {}\n    Fix: {}".format(*error))

        print()

    if len(repo.warnings) > 0:
        print("WARNINGS:")
        for warning in repo.warnings:
            print("  - {}: {}\n    Fix: {}".format(*warning))

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

    _doctor_parser = subparser.add_parser('doctor', description="Verify your environment settings and connectivity.",
                                          help='verify your enviornment for multipackage usage')

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
            retval = verify_environment()
        elif args.action == 'info':
            retval = verify_repo(args.repo)
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

