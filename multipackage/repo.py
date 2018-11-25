"""Main entry point for dealing with repositories."""

from __future__ import unicode_literals
import os
import json
import logging
from collections import namedtuple
from .exceptions import UsageError
from .utilities import atomic_json
from .manifest import ManifestFile


ErrorMessage = namedtuple("ErrorMessage", ['file', 'message', 'suggestion'])

class Repository:
    """High-level representation of an entire repository.

    This is the main class inside ``multipackage`` that processes a complete
    repository.  It reads two files from the repository:

      - multipackage.json: The overall settings for this repository
      - multipackage_manifest.json: A manifest file of all of the
        files multipackage is managing.

    Args:
        path (str): A path to the repository root directory.
    """

    SETTINGS_FILE = "multipackage.json"
    MANIFEST_FILE = "multipackage_manifest.json"
    SETTINGS_VERSION = "1.0"

    def __init__(self, path):
        self.path = path
        self._logger = logging.getLogger(__name__)

        if not os.path.exists(self.path):
            raise UsageError("Path '{}' should be a folder but it doesn't exist".format(path),
                             "Check your path")

        if not os.path.isdir(self.path):
            raise UsageError("Path {} is not a folder".format(path),
                             "Check your path")

        self.initialized = False
        self.options = {}
        self.errors = []
        self.warnings = []

        self._try_load()
        self.manifest = ManifestFile(os.path.join(path, self.MANIFEST_FILE), self)

    @property
    def clean(self):
        """Whether we have any errors."""

        return len(self.errors) == 0

    def _try_load(self):
        """Try to load settings for this repository."""

        settings_path = os.path.join(self.path, self.SETTINGS_FILE)
        if not os.path.exists(settings_path):
            return

        self.initialized = True

        try:
            with open(settings_path, "r") as infile:
                settings = json.load(infile)

            self._load_settings(settings)
        except IOError:
            self._logger.exception("Error opening file %s", settings_path)
            self.add_error(self.SETTINGS_FILE, "Could not load file due to IO error", "Check the file")
        except ValueError:
            self._logger.exception("Error loading json from file %s", settings_path)
            self.add_error(self.SETTINGS_FILE, "File does not contain valid json", "Verify the file's contents")

    def add_error(self, file, message, suggestion):
        """Record an error."""

        error = ErrorMessage(file, message, suggestion)
        self.errors.append(error)

    def add_warning(self, file, message, suggestion):
        """Record a warning."""

        error = ErrorMessage(file, message, suggestion)
        self.warnings.append(error)

    def _load_settings(self, settings):
        """Load and validate settings dictionary."""

        version = settings.get('version')
        if version is None:
            self.add_error(self.SETTINGS_FILE, "Missing required version key",
                            "Run `multipackage init --clean` or manually fix.")
        if version != self.SETTINGS_VERSION:
            self.add_warning(self.SETTINGS_FILE, "Old file version ({})".format(version),
                              "Run `multipackage update`")

        options = settings.get('settings', {})
        self.options = options

        # FIXME: Also load in manifest

    def initialize(self, clean=False):
        """Initialize or reinitialize this repository."""

        if self.initialized and not clean:
            raise UsageError("Cannot re-initialize an initialized repository unless --clean is passed",
                             "multipackage init --clean")
        settings = {
            'version': self.SETTINGS_VERSION,
            'options': {}
        }

        atomic_json(os.path.join(self.path, self.SETTINGS_FILE), settings)
        atomic_json(os.path.join(self.path, self.MANIFEST_FILE), {})
