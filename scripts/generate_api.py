"""Generate API docs for all subpackages."""

from __future__ import print_function
import sys
import os
import shutil
import time
import argparse

VERSION = "0.1.0"


class Error(Exception):
    """Exception that indicates an error message."""

    def __init__(self, message, code=1):
        super(Error, self).__init__(message)
        self.message = message
        self.exit_code = code


def delete_with_retry(folder):
    """Try multiple times to delete a folder.

    This is required on windows because of things like:
    https://bugs.python.org/issue15496
    https://blogs.msdn.microsoft.com/oldnewthing/20120907-00/?p=6663/
    https://mail.python.org/pipermail/python-dev/2013-September/128350.html
    """

    for _i in range(0, 5):
        try:
            if os.path.exists(folder):
                shutil.rmtree(folder)

            return
        except:  #pylint:disable=bare-except;We do really want to catch everything
            time.sleep(0.1)

    raise Error("Could not delete directory after 5 attempts, failing")


def build_parser():
    """Build an argument parser."""

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True, help="Output directory for saving the docs")
    parser.add_argument("-c", "--clean", action="store_true", help="Clean the output directory before starting")
    parser.add_argument("input", default=[], nargs="+", help="The input directories to generate docs for")
    parser.add_argument("-t", "--template", required=True, help="The template directory")
    parser.add_argument("-r", "--remove", action="append", default=[], help="Remove these generated files")
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=VERSION))
    return parser


def verify_output(path):
    """Verify that output path exists and is a directory.

    Args:
        path (str): The destination path.
    """

    if not os.path.exists(path):
        os.mkdir(path)
        return

    if not os.path.isdir(path):
        raise Error("Output directory exists and is not a directory: %s" % path)


def verify_packages():
    """Verify that we have all required packages."""

    try:
        import sphinx as _sphinx
    except ImportError:
        raise Error("This command requires sphinx: pip install sphinx")

    try:
        import jinja2 as _jinja2
    except ImportError:
        raise Error("This command requires jinja2: pip install jinja2")


def generate_api(input_path, template_dir, output_path, remove):
    """Generate api files for a given input folder."""

    # Do this import here so we can check for import errors before failing
    try:
        from better_apidocs import main as apidoc_main  #pylint:disable=relative-import;We need this logic so that we work when installed
    except ImportError:
        from .better_apidocs import main as apidoc_main


    args = ['better_apidocs', '-o', output_path, input_path, '-f', '-e', '-t', template_dir]
    apidoc_main(args)

    for to_remove in remove:
        path = os.path.join(output_path, to_remove)
        if os.path.exists(path):
            print("Removing %s" % path)
            os.remove(path)


def main(argv=None):
    """Main entry point for generate_api.py."""

    should_raise = argv is None

    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        verify_packages()
        verify_output(args.output)

        if args.clean:
            print("Cleaning output directory")
            delete_with_retry(args.output)
            verify_output(args.output)

        for input_folder in args.input:
            generate_api(input_folder, args.template, args.output, args.remove)

    except Error as exc:
        if should_raise:
            raise

        print("ERROR: %s" % exc.message)
        return exc.exit_code

    return 0


if __name__ == "__main__":
    sys.exit(main())
