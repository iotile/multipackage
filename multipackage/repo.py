"""Main entry point for dealing with repositories."""

from __future__ import unicode_literals
import os
import json
import logging
from builtins import open
from collections import namedtuple
from .exceptions import UsageError
from .utilities import atomic_json, ManagedFileSection, render_template, GITRepository
from .manifest import ManifestFile
from . import subsystems


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

    DEFAULT_TEMPLATE = "pypi_package"
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
        self.template = None
        self.version = None
        self.options = {}
        self.errors = []
        self.warnings = []

        self._try_load()
        self.manifest = ManifestFile(os.path.join(path, self.MANIFEST_FILE), self)

        self.git = GITRepository(self.path)

    @property
    def clean(self):
        """Whether we have any errors."""

        return len(self.errors) == 0

    @property
    def settings_changed(self):
        """Whether our settings file on disk has been changed."""

        status = self.manifest.verify_file(os.path.join(self.path, self.SETTINGS_FILE))
        return status != "unchanged"

    def github_slug(self):
        """Get the github slug from this repository.

        This is a string of the format user/repo_name.
        """

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
                           "Run `multipackage init --force` or manually fix.")
        if version != self.SETTINGS_VERSION:
            self.add_warning(self.SETTINGS_FILE, "Old file version ({})".format(version),
                             "Run `multipackage update`")

        self.template = settings.get('template', self.DEFAULT_TEMPLATE)
        self.options = settings.get('options', {})

    def initialize(self, clean=False, platforms=('macos', 'windows', 'linux'), python_versions=('2.7', '3.6')):
        """Initialize or reinitialize this repository."""

        if self.initialized and not clean:
            raise UsageError("Cannot re-initialize an initialized repository unless --force is passed",
                             "multipackage init --force")

        valid_platforms = ('macos', 'windows', 'linux')
        valid_python_versions = ('2.7', '3.6')

        for platform in platforms:
            if platform not in valid_platforms:
                raise UsageError("Invalid platform specified: %s" % platform,
                                 "Valid platform options are: %s" % valid_platforms)

        for python in python_versions:
            if python not in valid_python_versions:
                raise UsageError("Invalid python version specified: %s" % python,
                                 "Valid platform options are: %s" % valid_python_versions)

        settings = {
            'version': self.SETTINGS_VERSION,
            'template': self.DEFAULT_TEMPLATE,
            'options': {
                'test_matrix': {
                    'platforms': platforms,
                    'python_versions': python_versions
                }
            }
        }

        atomic_json(os.path.join(self.path, self.SETTINGS_FILE), settings)
        atomic_json(os.path.join(self.path, self.MANIFEST_FILE), {})

        self.manifest.update_file(os.path.join(self.path, self.SETTINGS_FILE), hash_type="json")
        self.manifest.save()

    def ensure_lines(self, relative_path, lines, delimiter_start='#', delimiter_end=''):
        """Ensure that the following lines are in the given file.

        This will create or update a ManagedSection and ensure that the
        following lines are all present in that file.  The lines are assumed
        to be unordered so they are added independently of each other.

        This method is idempotent. It will only add a line to the file if it
        does not already exist.

        The lines are automatically saved to disk.

        Args:
            relative_path (str): The relative path to the file that we want to
                update.
            lines (list of str): A list of strings to add to the given file if
                they do not exist.
            delimiter_start (str): The character string that starts a managed file
                section block header line.  This is usually a comment character
                like '#'.
            delimiter_end (str): Optional charcter string that ends
                a managed file section block header line.  This defaults to
                None but can be set to a value if comments need to be explicitly
                closed such as delimiter_start="<!-- ", delimiter_end=" -->".
        """

        path = os.path.join(self.path, relative_path)
        section = ManagedFileSection(path, delimiter_start=delimiter_start, delimiter_end=delimiter_end)
        section.ensure_lines(lines)

        self.manifest.update_file(path, hash_type="section")

    def ensure_template(self, relative_path, template, variables=None):
        """Ensure that the contents of a given file match a template.

        This function will render the given template shipped with the
        multipackage package.

        Args:
            relative_path (str): The relative path to the file that we want to
                update.
            template (str): The name of the template file to render
            variables (dict): A set of substitution variables to fill into
                the template.
        """

        path = os.path.join(self.path, relative_path)

        if variables is None:
            variables = {}

        render_template(template, variables, out_path=path)
        self.manifest.update_file(path)

    def update(self):
        """Update all of the managed files in this multipackage installation.

        This method delegates to all of the enabled multipackage subsystems to
        actually update each subcomponent.
        """

        if not self.initialized:
            raise UsageError("You must initialize a repository before updating it",
                             "multipackage init")

        if not self.clean:
            raise UsageError("Correct repository errors before updating",
                             "multipackage info")

        try:
            subsystems.BasicSubsystem(self).update(self.options)
            subsystems.LintingSubsystem(self).update(self.options)
            subsystems.TravisSubsystem(self).update(self.options)

            self.manifest.update_file(os.path.join(self.path, self.SETTINGS_FILE), hash_type='json')
        finally:
            self.manifest.save()
