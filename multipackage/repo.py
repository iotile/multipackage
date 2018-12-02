"""Main entry point for dealing with repositories."""

from __future__ import unicode_literals
import os
import re
import json
import shutil
import logging
from builtins import open
from collections import namedtuple
from .exceptions import UsageError, InternalError
from .utilities import atomic_json, ManagedFileSection, render_template, GITRepository
from .manifest import ManifestFile
from .templates import PyPIPackageTemplate


ErrorMessage = namedtuple("ErrorMessage", ['file', 'message', 'suggestion'])
Component = namedtuple("Component", ['name', 'relative_path', 'options'])


class Repository(object):
    """High-level representation of an entire repository.

    This is the main class inside ``multipackage`` that processes a complete
    repository.  It reads two files from the repository:

      - multipackage.json: The overall settings for this repository
      - multipackage_manifest.json: A manifest file of all of the
        files multipackage is managing.

    Args:
        path (str): A path to the repository root directory.
        nogit (bool): Optional parameter to support creating a repository
            from a non-git repository.  This is useful for testing purposes.
    """

    DEFAULT_TEMPLATE = "pypi_package"
    MULTIPACKAGE_DIR = ".multipackage"
    SCRIPT_DIR = os.path.join(MULTIPACKAGE_DIR, "scripts")

    SETTINGS_FILE = os.path.join(MULTIPACKAGE_DIR, "settings.json")
    MANIFEST_FILE = os.path.join(MULTIPACKAGE_DIR, "manifest.json")
    COMPONENT_FILE = os.path.join(MULTIPACKAGE_DIR, "components.txt")

    COMPONENT_REGEX = r"^(?P<package>[a-zA-Z_0-9]+):\s*(?P<path>[\.a-zA-Z_\-0-9\\/]+)(?P<options>(\s*,\s*[a-zA-Z_0-9_]+\s*=\s*[a-zA-Z_0-9_]+)+)?$"
    SETTINGS_VERSION = "0.1"

    def __init__(self, path, nogit=False):
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
        self.author = None
        self.name = None
        self.options = {}
        self.errors = []
        self.warnings = []
        self.components = {}
        self.subsystems = []

        template_name = self._try_load()
        self.manifest = ManifestFile(os.path.join(self.path, self.MANIFEST_FILE), self.path, self)

        if nogit:
            self.git = None
        else:
            self.git = GITRepository(self.path)

        if self.initialized:
            self._try_load_components()

            if template_name != "pypi_package":
                raise UsageError("Templates other than 'pypi_package' are not yet supported.")

            self.template = PyPIPackageTemplate()
            self.template.install(self)

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

        if self.git is None:
            raise InternalError("You cannot call github_slug() if you pass nogit to the constructor")

        org, repo = self.git.github_name()
        return "{}/{}".format(org, repo)

    def _try_load_components(self):
        """Try to load the list of components from this repository.

        The format of the components text file is a list of lines:
        <package_name>: <relative_path>[,name1=value1]*

        Whitespace is ignored around options, which begin after the first
        comma.
        """

        component_path = os.path.join(self.path, self.COMPONENT_FILE)
        if not os.path.exists(component_path):
            self.add_warning(self.COMPONENT_FILE, "Missing components list", "Run `multipackage update` to reinitialize")
            return

        with open(component_path, "r", encoding="utf-8") as infile:
            lines = infile.readlines()

        regex = re.compile(self.COMPONENT_REGEX)

        for line in lines:
            line = line.strip()
            if line.startswith('#') or len(line) == 0:
                continue

            result = regex.match(line)
            if result is None:
                self.add_error(self.COMPONENT_FILE, "Could not parse line '%s' in components file" % line,
                               "Manually fix the file, verify with `multipackage info` and then run `multipackage update`")
                continue

            package, path, option_string = result.group("package", "path", "options")
            options = self._parse_options_string(option_string)

            if not os.path.isdir(os.path.join(self.path, path)):
                self.add_error(self.COMPONENT_FILE, "Component folder '%s' specified in components file is not a directory" % path,
                               "Manually fix the file, verify with `multipackage info` and then run `multipackage update`")
                continue

            component = Component(package, path, options)
            self._logger.debug("Adding component %s", component)
            self.components[package] = component

    def _parse_options_string(self, option_string):
        if option_string is None:
            return {}

        option_assignments = option_string.split(',')

        options = {}

        for assignment in option_assignments:
            assignment = assignment.strip()
            if len(assignment) == 0:
                continue

            name, _, value = assignment.partition('=')
            name = name.strip()
            value = value.strip()

            if len(name) == 0 or len(value) == 0:
                self._logger.debug("Skipping empty option assignment: %s", assignment)

            if name in options:
                self._logger.debug("Overwriting option that appeared twice: %s", name)

            options[name] = value

        return options

    def _try_load(self):
        """Try to load settings for this repository."""

        settings_path = os.path.join(self.path, self.SETTINGS_FILE)
        if not os.path.exists(settings_path):
            return

        self.initialized = True

        try:
            with open(settings_path, "r") as infile:
                settings = json.load(infile)

            return self._load_settings(settings)
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

    def add_subsystem(self, subsystem):
        """Add a subsystem to this repository."""
        self.subsystems.append(subsystem)

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

        # FIXME: The template class should handle checking for outdated versions
        if version != self.SETTINGS_VERSION:
            self.add_warning(self.SETTINGS_FILE, "Old file version ({})".format(version),
                             "Run `multipackage update`")

        self.author = settings.get('author', "Unknown Author")
        self.name = settings.get('name', "Unknown Project")

        self.options = settings.get('options', {})
        return settings.get('template', self.DEFAULT_TEMPLATE)

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

        self.ensure_directory(os.path.join(self.path, self.MULTIPACKAGE_DIR))
        self.ensure_directory(os.path.join(self.path, self.SCRIPT_DIR))

        atomic_json(os.path.join(self.path, self.SETTINGS_FILE), settings)
        atomic_json(os.path.join(self.path, self.MANIFEST_FILE), {})

        self.manifest.update_file(os.path.join(self.path, self.SETTINGS_FILE), hash_type="json")

        # Make sure we start off with a blank components file if it doesn't exist already
        self.ensure_template(os.path.join(self.path, self.COMPONENT_FILE), template="components.txt", overwrite=False)

        self.manifest.save()

    def ensure_lines(self, relative_path, lines, match=None, present=True, multi=False, delimiter_start='#', delimiter_end=''):
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
            present (bool): If True, ensure lines are present (the default), if
                False, ensure lines are absent.
            match (list of str): A list of regular expressions to
                use to match against a line.  If passed it must have the same
                length as lines and will be paired with each line in lines in
                order to determine which line matches.
            multi (bool): If true, allow for matching and updating multiple lines
                for each line in ``lines``.  If False, InternalError is raised
                if there are multiple lines matching a given line.
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
        section.ensure_lines(lines, match, present=present, multi=multi)

        self.manifest.update_file(path, hash_type="section")

    def ensure_directory(self, relative_path, gitkeep=False):
        """Ensure that a given directory exists.

        Args:
            relative_path (str): The relative path to the directory that we
                wish to check.
            gitkeep (bool): Also insert an unmanaged .gitkeep file to ensure
                the directory is saved in the git repo history.
        """

        path = os.path.join(self.path, relative_path)
        if os.path.exists(path) and not os.path.isdir(path):
            raise UsageError("Cannot create directory, a file is in its place: %s" % relative_path, "Remove or rename the file to make space for the directory")

        if not os.path.exists(path):
            os.mkdir(path)

        if gitkeep:
            gitkeep_path = os.path.join(path, ".gitkeep")
            if not os.path.exists(gitkeep_path):
                with open(gitkeep_path, "wb"):
                    pass

    def ensure_script(self, relative_path, source, present=True, overwrite=True):
        """Ensure that a script file is copied.

        This function will copy or remove the given script file. All script
        files come from the multipackage/data/scripts folder.

        Args:
            relative_path (str): The relative path to the file that we want to
                update.
            source (str): The name of the template file to render
            present (bool): If True, ensure lines are present (the default), if
                False, ensure lines are absent.
            overwrite (bool): Overwrite the file if it exists already. Setting this
                to False will ensure that the file is added only if is absent,
                allowing for initializing files that are not present without
                subsequently overwriting them.
        """

        from pkg_resources import resource_filename, Requirement

        path = os.path.join(self.path, relative_path)

        if present is False:
            self.manifest.remove_file(path, force=True)
            if os.path.exists(path):
                os.remove(path)

            return

        if overwrite is False and os.path.exists(path):
            return

        source_path = os.path.join(resource_filename(Requirement.parse("multipackage"), "multipackage/data/scripts"), source)
        shutil.copyfile(source_path, path)

        self.manifest.update_file(path)

    def ensure_template(self, relative_path, template, variables=None, present=True, overwrite=True, raw=False):
        """Ensure that the contents of a given file match a template.

        This function will render the given template shipped with the
        multipackage package.

        Args:
            relative_path (str): The relative path to the file that we want to
                update.
            template (str): The name of the template file to render
            variables (dict): A set of substitution variables to fill into
                the template.
            present (bool): If True, ensure lines are present (the default), if
                False, ensure lines are absent.
            overwrite (bool): Overwrite the file if it exists already. Setting this
                to False will ensure that the file is added only if is absent,
                allowing for initializing files that are not present without
                subsequently overwriting them.
            raw (bool): Do not actually fill in the template, just copy it into place.
                This is useful if the file itself is a jinja2 template that should
                be rendered later.
        """

        path = os.path.join(self.path, relative_path)

        if present is False:
            self.manifest.remove_file(path, force=True)
            if os.path.exists(path):
                os.remove(path)

            return

        if overwrite is False and os.path.exists(path):
            return

        if raw:
            from pkg_resources import resource_filename, Requirement
            source_path = os.path.join(resource_filename(Requirement.parse("multipackage"), "multipackage/data/templates"), template)
            shutil.copyfile(source_path, path)
        else:
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
            for subsystem in self.subsystems:
                subsystem.update(self.options)

            self.manifest.update_file(os.path.join(self.path, self.SETTINGS_FILE), hash_type='json')
            self.manifest.update_file(os.path.join(self.path, self.COMPONENT_FILE))
        finally:
            self.manifest.save()
