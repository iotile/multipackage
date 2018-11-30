"""A hash based manifest file."""

import os.path
import json
import logging
from builtins import open
from collections import namedtuple
from future.utils import viewitems
from .utilities import line_hash, dict_hash, atomic_json, ManagedFileSection
from .exceptions import InternalError

VALID = 0
NOT_PRESENT = 1
INVALID_HASH = 2
PRESENT_UNKNOWN = 3

ManagedFile = namedtuple("ManagedFile", ["relative_path", "absolute_path", "status", "expected_hash", "hash_type"])

class ManifestFile:
    """A hash based manifest file.

    This class will load a json file that contains relative file paths and
    hash values.  It can detect changes in the files using the hashes.

    Args:
        path (str): The path to the manifest file.  If it does not exist it
            will be initialized as empty.
        base_path (str): The base path that will be used to store relative
            paths for keys.
        reporter (object): An error reporter class that has an add_warning
            and add_error method.  This is compatible with the signatures
            of the Repository class so it can be passed directly.
    """

    def __init__(self, path, base_path, reporter):
        self.path = path
        self._relative_base = os.path.abspath(base_path)
        self._relative_path = os.path.relpath(path, start=self._relative_base)
        self._logger = logging.getLogger(__name__)
        self._reporter = reporter
        self.files = {}

        self._try_load()

    def _try_load(self):
        if not os.path.exists(self.path):
            self._reporter.add_error(self._relative_path, "Manifest file does not exist",
                                     "Run `multipackage init --force`")
            return

        try:
            with open(self.path, "r") as infile:
                data = json.load(infile)
        except ValueError:
            self._logger.exception("Error parsing manifest file %s", self.path)
            self._reporter.add_error(self._relative_path, "Could not parse JSON in manifest file",
                                     "Run `multipackage init --force`")
            return
        except IOError:
            self._logger.exception("Error loading manifest file %s", self.path)
            self._reporter.add_error(self._relative_path, "Could not load manifest file",
                                     "Run `multipackage init --force`")
            return

        for key, value in viewitems(data):
            status = PRESENT_UNKNOWN
            path = os.path.join(self._relative_base, key)
            if not os.path.exists(path):
                status = NOT_PRESENT

            hash_value = value.get('hash')
            hash_type = value.get('hash_type')

            if hash_value is None or hash_type is None:
                self._logger.error("Invalid manifest file entry for key %s: %s", key, value)
                self._reporter.add_error(self._relative_path, "Invalid manifest entry for key %s" % key,
                                         "Run `multipackage init --force`")
                continue

            self.files[key] = ManagedFile(key, path, status, hash_value, hash_type)

    def verify_all(self, report=False):
        """Verify the hashes of all managed files.

        Args:
            report (bool): Report errors for all invalid files.
        """

        for key, info in viewitems(self.files):
            status = NOT_PRESENT

            actual_hash = self._load_file(info.absolute_path, hash_type=info.hash_type)
            if actual_hash is not None and actual_hash != info.expected_hash:
                self._logger.error("Invalid hash for file %s, found %s, expected: %s",
                                   info.absolute_path, actual_hash, info.expected_hash)

                status = INVALID_HASH

                if report:
                    self._reporter.add_error(key, "File hash does not match",
                                             "Run `multipackage update`")

            self.files[key] = ManagedFile(key, info.absolute_path, status, info.expected_hash, info.hash_type)

    def verify_file(self, path):
        """Verify the status of a given file.

        The argument should be the path to a given file.  If the file is
        not inside the manifest an InternalError is raised.  Otherwise
        this method will return a string indicating the file's status.

        Args:
            path (str): The path to the file to check.

        Returns:
            str: The status of the file.

            Possible options are:

              - not_present: The file is not present
              - changed: The file is present but does not match the
                recorded hash.
              - unchanged: The file is present and its hash is the
                same as what was recorded.
        """

        key = self._make_key(path)

        info = self.files.get(key)
        if info is None:
            raise InternalError("ManifestFile.verify_file called on file that is not in the manifest: %s" % path)

        actual_hash = self._load_file(info.absolute_path, hash_type=info.hash_type)
        if actual_hash is None:
            return "not_present"

        if actual_hash == info.expected_hash:
            return "unchanged"

        return "changed"

    def update_file(self, path, hash_type="line"):
        """Add or update the hash for a given file.

        If the file does not exist, an error is logged and the file is added
        to the manifest as NOT_PRESENT.  Otherwise it is added with the
        correct hash value.

        The new manifest data is written out automatically back to the
        manifest file on disk.

        Args:
            path (str): The path to the file that we wish to add to the
                manifest.
            hash_type (str): Optional specifier of how to calculate the file's
                hash. Supported options are line, json or section.  ``line``
                means that the lines are hashed one at a time with line
                endings ignored. ``json`` means that the file is valid json
                which is loaded and then the dict is normalized and hashed.
                ``section`` means that a section of the file is managed while
                the rest is not.  Default: "line"
        """

        if hash_type not in ('line', 'json', 'section'):
            self._logger.error("Invalid hash type in update_file: %s, supported: line, json", hash_type)
            raise InternalError("update_file called with invalid hash type: %s" % hash_type)

        abspath = os.path.abspath(path)
        actual_hash = self._load_file(path, hash_type=hash_type)
        key = self._make_key(path)

        if actual_hash is None:
            status = NOT_PRESENT
            self._logger.error("ManifestFile.update_file called on path that does not exist: %s", path)
        else:
            status = VALID

        info = ManagedFile(key, abspath, status, actual_hash, hash_type)
        self.files[key] = info

    def remove_file(self, path, force=False):
        """Remove a managed file from the manifest.

        This will remove the entry from this manifest for the file.
        If the entry does not exist and force is False, an exception will
        be raised.  If force is True, then this error will be silently ignored.

        This method does not actually touch the file on disk, it just removes
        the corresponding entry in this manifest file.

        Args:
            path (str): The path to the file to remove.
            force (bool): Whether we should throw an error if the file is not
                present in the manifest.  Default is False, which means throw
                an error.
        """

        key = self._make_key(path)
        if key not in self.files and not force:
            self._logger.error("Attempted to remove unkown file %s from manifest", path)
            raise InternalError("Attempted to remove file %s from Manifest but it was not present" % path, "Try using ManifestFile.remove_file(path, force=True)")

        if key in self.files:
            del self.files[key]

    def save(self):
        """Atomically save this file to disk."""

        data = {key: {'hash': info.expected_hash, 'hash_type': info.hash_type} for key, info in viewitems(self.files)}
        atomic_json(self.path, data)

    def _make_key(self, path):
        abspath = os.path.abspath(path)
        key = os.path.normpath(os.path.relpath(abspath, self._relative_base))

        key = key.replace('\\', '/')
        return key

    @classmethod
    def _load_file(cls, path, hash_type="line", delimiter_start='#', delimiter_end=''):
        if not os.path.exists(path):
            return None

        if hash_type == 'line':
            with open(path, "r", encoding="utf-8", newline='') as infile:
                lines = infile.readlines()

            return line_hash(lines)
        elif hash_type == 'json':
            with open(path, "r") as infile:
                data = json.load(infile)
                return dict_hash(data)
        elif hash_type == 'section':
            section = ManagedFileSection(path, delimiter_start=delimiter_start,
                                         delimiter_end=delimiter_end)

            return section.actual_hash

        raise InternalError("ManifestFile._load_file called with invalid hash type: %s" % hash_type)
