"""Release script to automatically release a component onto pypi."""

from __future__ import (absolute_import, division, print_function, unicode_literals)

from getpass import getpass
import sys
import os
import argparse
import glob
import subprocess

import requests
import setuptools.sandbox
from twine.commands.upload import upload
from twine.settings import Settings

if sys.version_info.major < 3:
    from builtins import raw_input as input

try:
    from shared_errors import MismatchError, ExternalError, InternalError, handle_exception  #pylint:disable=relative-import;We need this logic so that we work when installed
except ImportError:
    from .shared_errors import MismatchError, ExternalError, InternalError, handle_exception

try:
    from release_notes import get_release_notes, get_version  #pylint:disable=relative-import;We need this logic so that we work when installed
except ImportError:
    from .release_notes import get_release_notes, get_version


VERSION = "0.1.0"


DESCRIPTION = \
"""Release script to automatically release a component onto PyPI.

This script will inspect the python package at <path> and verify that it has
the correct information before releasing.  You can check that everything is
ready for a release by passing -c,--check to do everything except upload the
finished distributions to PyPI (including sending a test message to slack if
configured so that you can check your webhook settings).


choosing your repo:
  You can specify the destination pypi index in one of four ways:

  - do nothing, the default behavior is to upload to PyPI
  - pass -r (pypi|testpypi).  These strings are automatically matched to the
    global PyPI index and the test pypi index, respectively.
  - pass -r <url>.  You can specify the URL for an arbitrary public or private
    PyPI index such as gemfury.
  - pass -r <name> where <name> is anything defined in your ~/.pypirc file (if
    it exists).

  Most users will not need to specify anything with -r since they will be
  uploading to PyPI, however, you can override this if you have a different
  target destination.

  Note that if you repo does not require a password, you still need to pass a
  blank one on the command line with --password= otherwise you will be
  prompted to enter one interactively.
"""


def build_parser():
    """Create an argument parser."""
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', default='.', nargs="?", help="The path to the component that we should release")
    parser.add_argument('-c', '--compat', default="universal", choices=['universal', 'python2', 'python3'], help="The python version we should release for")
    parser.add_argument('-e', '--expected', required=True, help="The expected version of the component")
    parser.add_argument('-s', '--slack', help="Optional slack web hook URL")
    parser.add_argument('-u', '--user', help="Username for the PyPI repo you are uploading to")
    parser.add_argument('-p', '--password', help="Password for the PyPI repo you are uploading to")
    parser.add_argument('-r', '--repo', help="The pypi repo you want to upload to")
    parser.add_argument('-k', '--check', action="store_true", help="Check that the release could proceed without actually releasing")
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=VERSION))

    return parser


def verify_python_version(expected):
    """Verify that we are on an appropriate python version to do the release."""

    if expected not in ('universal', 'python2', 'python3'):
        raise InternalError("Unknown expected python version string: %s" % expected)

    if sys.version_info[:2] < (2, 7):
        raise MismatchError("python interpreter version", ">=2.7", sys.version)

    if expected == "universal":
        return

    if expected == "python2" and sys.version_info.major >= 3:
        raise MismatchError("python interpreter version", "2.X", sys.version)
    elif expected == "python3" and sys.version_info.major < 3:
        raise MismatchError("python interpreter version", "3.X", sys.version)


def generate_slack_message(distribution, version, notes, check=False):
    """Format a nice slack message about the release."""

    notes = "```\n" + notes.strip() + "```"

    if check is False:
        color = "#2eb886"
    else:
        color = "#808080"

    attachment = {
        "color": color,
        "title": "Released {}-{} to PyPI".format(distribution, version),
        "fields": [
            {
                "title": "Distribution",
                "value": distribution,
                "short": True
            },
            {
                "title": "Version",
                "value": version,
                "short": True
            }
        ]
    }

    notes_attachment = {
        "color": color,
        "mrkdn_in": ["text"],
        "title": "Release Notes for {}-{}".format(distribution, version),
        "text": notes
    }

    fallback = "Released {}-{} to PyPI".format(distribution, version)
    if check:
        fallback = "Test message from release bot for {}-{}".format(distribution, version)
        attachment['text'] = "*This is just a test message, nothing was actually released.*"

    return {
        "fallback": fallback,
        "attachments": [
            attachment,
            notes_attachment
        ],
        'username': 'Release Bot'
    }


def send_slack_message(webhook, message_json):
    """Send a message to a slack channel."""

    resp = requests.post(webhook, json=message_json)
    if resp.status_code != 200:
        raise ExternalError("slack webhook", "Could not post message to slack channel: response=%d" % resp.status_code)


def check_component(path, expected_version):
    """Make sure the package version in setuptools matches what we expect it to be."""

    actual_version = get_version(path)

    if actual_version != expected_version:
        raise MismatchError("component version in version.py", expected_version, actual_version)


def build_component(component, universal):
    """Create an sdist and a wheel for the desired component."""

    curr = os.getcwd()
    os.chdir(component)
    try:
        name = subprocess.check_output(['python', 'setup.py', '--name'])
        if not isinstance(name, str):
            name = name.decode('utf-8')

        args = ['clean', 'sdist', 'bdist_wheel']
        if universal:
            args.append('--universal')

        setuptools.sandbox.run_setup('setup.py', args)
    finally:
        os.chdir(curr)

    return name.strip()


def upload_component(component_path, repo="pypi", username=None, password=None):
    """Upload a given component to pypi

    The pypi username and password must either be specified in a ~/.pypirc
    file or in environment variables PYPI_USER and PYPI_PASS
    """

    if username is None:
        username = input("Enter your username [%s]: " % repo)

    if password is None:
        password = getpass(("Enter your password [%s]: " % repo).encode('utf-8'))


    distpath = os.path.join(component_path, 'dist', '*')
    distpath = os.path.realpath(os.path.abspath(distpath))
    dists = glob.glob(distpath)

    repo_name = repo
    repo_url = None
    if "://" in repo_name:
        repo_url = repo
        repo_name = None

    try:
        #Invoke upload this way since subprocess call of twine cli has cross platform issues
        settings = Settings(username=username, password=password, repository_name=repo_name,
                            repository_url=repo_url)
        upload(settings, dists)
    except requests.exceptions.HTTPError as exc:
        code = exc.response.status_code

        if repo_name is None:
            repo_name = repo_url

        msg = "Unknown response from server"
        if code == 409 or code == 400:
            msg = "Package already exists"

        raise ExternalError("PyPI repository '%s'" % repo_name, "HTTP status %d: %s" % (code, msg))


def main(argv=None):
    """Main entrypoint for release_component.py script."""

    should_raise = True
    if argv is None:
        should_raise = False
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    retval = 0
    try:
        print("\n ---- Verifying python version is compatible ----\n")
        verify_python_version(args.compat)

        print("\n ---- Verifying component information is correct ----\n")

        check_component(args.path, args.expected)
        release_notes = get_release_notes(args.path, args.expected)

        print("Release Notes:")
        print(release_notes)

        print("\n ---- Building component ----\n")
        component_name = build_component(args.path, universal=args.compat == "universal")

        print("\n**** Successfully built distribution named '%s' ****" % component_name)

        if not args.check:
            print("\n ---- Uploading distributions ----\n")

            upload_component(args.path, args.repo, args.user, args.password)

        if args.slack is not None:
            print("\n ---- Notifying Slack Channel ----\n")

            msg = generate_slack_message(component_name, args.expected, release_notes, args.check)
            send_slack_message(args.slack, msg)

    except (MismatchError, InternalError, ExternalError, KeyboardInterrupt) as exc:
        if should_raise:
            raise

        retval = handle_exception(exc)

    return retval


if __name__ == '__main__':
    sys.exit(main())
