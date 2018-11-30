"""Helper script for parsing release notes from a markdown file."""

from __future__ import (absolute_import, division, print_function, unicode_literals)

import sys
import os
import argparse

try:
    from shared_errors import MismatchError, ExternalError, InternalError, handle_exception  #pylint:disable=relative-import;We need this logic so that we work when installed
except ImportError:
    from .shared_errors import MismatchError, ExternalError, InternalError, handle_exception


VERSION = "0.1.0"

DESCRIPTION = \
"""Parse a markdown file containing release notes.

This script will expect a file named RELEASE.md in <path> and will parse it as
if it contains a series of release notes.  The file must be formatted with
markdown containing the releases as second level headers: `##`.

The formatting for each release header line is flexible but must at least
match the following structure:

## [v]X.Y.Z [whatever you want]

Basically the line is read and the initial ## is discarded, any preceding
whitespace is stripped using lstrip() and then the first white-space delimited
word must be the version in X.Y.Z format.  It can optionally have a lower-case
v in front of it, which is stripped away if present.  So the following are all
valid ways of specifying version 1.5.0:

## 1.5.0 (11/28/2018)
##1.5.0
## v1.5.0 - 11/28/2018
## 1.5.0 hello this is a test

All lines after each valid release header are assumed to be the release notes
for that release (until the next header).
"""


def build_parser():
    """Build our argument parser."""

    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('path', default='.', nargs="?", help="The path to the component that we should release")
    parser.add_argument('-r', '--release', help="The release notes version we want")
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=VERSION))

    return parser


def get_version(path):
    """Get the version of package."""

    compath = os.path.realpath(os.path.abspath(path))

    if sys.path[0] != compath:
        sys.path.insert(0, compath)

    try:
        import version
    except ImportError:
        raise ExternalError("version.py", "Missing version.py file containing a version = \"X.Y.Z\" line")

    if not hasattr(version, "version"):
        raise ExternalError("version.py", "File is missing a version = \"X.Y.Z\" line")

    return version.version


def parse_release_header(version_line, prefix="##"):
    """Parse a version from a markdown header.

    The line must be formatted as:
    ## [v]X.Y.Z [whatever else you want]

    So you could have, for example:
    ## 1.5.0 (11/28/2018)
    ##1.5.0
    ## v1.5.0 - 11/28/2018
    ## 1.5.0 hello this is a test

    Returns:
        str: The parsed version.
    """

    if not version_line.startswith(prefix):
        return None

    version_line = version_line[len(prefix):].lstrip()

    if len(version_line) == 0:
        return None

    words = version_line.split()
    if len(words) == 0:
        return None

    version_word = words[0]
    if version_word.startswith('v'):
        version_word = version_word[1:]

    return version_word


def get_release_notes(path, version):
    """Get a release notes section from a markdown file."""

    if os.path.isdir(path):
        path = os.path.join(path, 'RELEASE.md')

    if not os.path.isfile(path):
        raise ExternalError(path, "Path is not a file or a folder containing a RELEASE.md file: %s" % path)

    try:
        with open(path, "r") as infile:
            lines = infile.readlines()
    except IOError:
        raise ExternalError("Release notes file '%s" % path, "Could not open file to read release notes")

    lines = [x.rstrip() for x in lines]
    release_lines = {parse_release_header(line): i for i, line in enumerate(lines) if line.startswith('##')}

    if version not in release_lines:
        raise MismatchError("release notes entry for release", version, "%d non-matching release headers" % len(release_lines))

    start_line = release_lines[version]
    past_releases = [x for x in release_lines.values() if x > start_line]

    if len(past_releases) == 0:
        release_string = "\n".join(lines[start_line + 1:])
    else:
        release_string = "\n".join(lines[start_line + 1:min(past_releases)])

    if len(release_string) == 0:
        raise MismatchError("release notes contents for release", "a list of release notes", "nothing")

    return release_string


def main(argv=None, should_raise=True):
    """Main entry point for release_notes.py."""

    if argv is None:
        should_raise = False
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    retval = 0

    try:
        if os.path.isfile(args.path):
            base_dir = os.path.dirname(args.path)
        else:
            base_dir = args.path

        release = args.release
        source_string = ""
        if release is None:
            release = get_version(base_dir)
            source_string = " (version pulled from version.py, use --release version to override)"
        notes = get_release_notes(args.path, release)

        print()
        print("Release Notes for Version %s%s:" % (release, source_string))
        print(notes)

    except (MismatchError, InternalError, ExternalError, KeyboardInterrupt) as exc:
        if should_raise:
            raise

        retval = handle_exception(exc)

    return retval


if __name__ == '__main__':
    sys.exit(main())
