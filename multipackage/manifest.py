"""A hash based manifest file."""

import os.path
import json
import logging
from collections import namedtuple
from future.utils import viewitems
from .utilities import line_hash

VALID = 0
NOT_PRESENT = 1
INVALID_HASH = 2
PRESENT_UNKNOWN = 3

ManagedFile = namedtuple("MangedFile", ["relative_path", "absolute_path", "status", "expected_hash"])

class ManifestFile:
    """A hash based manifest file.

    This class will load a json file that contains relative file paths and
    hash values.  It can detect changes in the files using the hashes.

    Args:
        path (str): The path to the manifest file.  If it does not exist it
            will be initialized as empty.
        reporter (object): An error reporter class that has an add_warning
            and add_error method.  This is compatible with the signatures
            of the Repository class so it can be passed directly.
    """

    def __init__(self, path, reporter):
        self.path = path
        self._relative_base = os.path.abspath(os.path.dirname(path))
        self._relative_path = os.path.relpath(path, start=self._relative_base)
        self._logger = logging.getLogger(__name__)
        self._reporter = reporter
        self.files = {}

        self._try_load()

    def _try_load(self):
        if not os.path.exists(self.path):
            self._reporter.add_error(self._relative_path, "Manifest file does not exist",
                                     "Run `multipackage init --clean`")
            return

        try:
            with open(self.path, "r") as infile:
                data = json.load(infile)
        except ValueError:
            self._logger.exception("Error parsing manifest file %s", self.path)
            self._reporter.add_error(self._relative_path, "Could not parse JSON in manifest file",
                                     "Run `multipackage init --clean`")
            return
        except IOError:
            self._logger.exception("Error loading manifest file %s", self.path)
            self._reporter.add_error(self._relative_path, "Could not load manifest file",
                                     "Run `multipackage init --clean`")
            return

        for key, value in viewitems(data):
            status = PRESENT_UNKNOWN
            path = os.path.join(self._relative_base, key)
            if not os.path.exists(path):
                status = NOT_PRESENT

            self.files[key] = ManagedFile(key, path, status, value)

    def verify_files(self, report=False):
        """Verify the hashes of all managed files.

        Args:
            report (bool): Report errors for all invalid files.
        """

        for key, info in viewitems(self.files):
            status = NOT_PRESENT
            if os.path.exists(info.absolute_path):
                with open(info.absolute_path, "r", encoding="utf-8", newline='') as infile:
                    lines = infile.readlines()

            actual_hash = line_hash(lines)
            if actual_hash != info.expected_hash:
                self._logger.error("Invalid hash for file %s, found %s, expected: %s",
                                   info.absolute_path, actual_hash, info.expected_hash)

                status = INVALID_HASH

                if report:
                    self._reporter.add_error(key, "File hash does not match",
                                             "Run `multipackage init --clean`")

            self.files[key] = ManagedFile(key, info.absolute_path, status, info.expected_hash)
