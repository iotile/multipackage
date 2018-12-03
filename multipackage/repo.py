"""Main entry point for dealing with repositories."""

from __future__ import unicode_literals
import os
import re
import json
import shutil
import logging
from builtins import open
from collections import namedtuple
from .exceptions import UsageError, InternalError, InvalidEnvironmentError, InvalidSettingError
from .utilities import atomic_json, ManagedFileSection, render_template
from .manifest import ManifestFile
from .templates import PyPIPackageTemplate


Message = namedtuple("Message", ['file', 'message', 'suggestion', 'type'])
Component = namedtuple("Component", ['name', 'relative_path', 'options'])
EnvironmentVariable = namedtuple("EnvironmentVariable", ['name', 'subsystem', 'contexts', 'usage', 'required', 'verify'])

_MISSING = object()


class Repository(object):
    """High-level representation of an entire repository.

    This is the main class inside ``multipackage`` that processes a complete
    repository.  It reads two files from the repository:

      - .multipackage/settings.json: The overall settings for this repository
      - .multipackage/manifest.json: A manifest file of all of the files
        multipackage is managing including hashes to check for changes.

    Using these files, the Repository class will load in the correct
    repository template that informs it what other files are managed and how
    to parse the settings stored inside ``settings.json``.

    Args:
        path (str): A path to the repository root directory.
    """

    DEFAULT_TEMPLATE = "pypi_package"
    MULTIPACKAGE_DIR = ".multipackage"
    SETTINGS_VERSION = "0.1"

    SCRIPT_DIR = os.path.join(MULTIPACKAGE_DIR, "scripts")
    SETTINGS_FILE = os.path.join(MULTIPACKAGE_DIR, "settings.json")
    MANIFEST_FILE = os.path.join(MULTIPACKAGE_DIR, "manifest.json")
    COMPONENT_FILE = os.path.join(MULTIPACKAGE_DIR, "components.txt")

    COMPONENT_REGEX = r"^(?P<package>[a-zA-Z_0-9]+):\s*(?P<path>[\.a-zA-Z_\-0-9\\/]+)(?P<options>(\s*,\s*[a-zA-Z_0-9_]+\s*=\s*[a-zA-Z_0-9_]+)+)?$"

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
        self.author = None
        self.name = None
        self.options = {}
        self.components = {}
        self.subsystems = []

        self._messages = []
        self._env_variables = {}
        self._original_settings = {}

        template_name = self._try_load()
        self.manifest = ManifestFile(os.path.join(self.path, self.MANIFEST_FILE), self.path, self)

        if self.initialized:
            self._try_load_components()

            if template_name != self.DEFAULT_TEMPLATE:
                raise UsageError("Templates other than '{}' are not yet supported.".format(self.DEFAULT_TEMPLATE))

            self.template = PyPIPackageTemplate()
            self.template.install(self)

    @property
    def clean(self):
        """Whether we have any errors."""

        return self.count_messages('error') == 0

    @property
    def settings_changed(self):
        """Whether our settings file on disk has been changed."""

        status = self.manifest.verify_file(os.path.join(self.path, self.SETTINGS_FILE))
        return status != "unchanged"

    def _try_load_components(self):
        """Try to load the list of components from this repository.

        The format of the components text file is a list of lines:
        <package_name>: <relative_path>[,name1=value1]*

        Whitespace is ignored around options, which begin after the first
        comma.
        """

        component_path = os.path.join(self.path, self.COMPONENT_FILE)
        if not os.path.exists(component_path):
            self.warning(self.COMPONENT_FILE, "Missing components list", "Run `multipackage update` to reinitialize")
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
                self.error(self.COMPONENT_FILE, "Could not parse line '%s' in components file" % line,
                           "Manually fix the file, verify with `multipackage info` and then run `multipackage update`")
                continue

            package, path, option_string = result.group("package", "path", "options")
            options = self._parse_options_string(option_string)

            if not os.path.isdir(os.path.join(self.path, path)):
                self.error(self.COMPONENT_FILE, "Component folder '%s' specified in components file is not a directory" % path,
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
            return None

        self.initialized = True

        try:
            with open(settings_path, "r") as infile:
                settings = json.load(infile)

            return self._load_settings(settings)
        except IOError:
            self._logger.exception("Error opening file %s", settings_path)
            self.error(self.SETTINGS_FILE, "Could not load file due to IO error", "Check the file")
        except ValueError:
            self._logger.exception("Error loading json from file %s", settings_path)
            self.error(self.SETTINGS_FILE, "File does not contain valid json", "Verify the file's contents")

    def error(self, file, message, suggestion):
        """Record an error."""

        err = Message(file, message, suggestion, type="error")
        self._messages.append(err)

    def warning(self, file, message, suggestion):
        """Record a warning."""

        warn = Message(file, message, suggestion, type="warning")
        self._messages.append(warn)

    def info(self, file, message, suggestion):
        """Record an info message."""

        msg = Message(file, message, suggestion, type="info")
        self._messages.append(msg)

    def iter_messages(self, message_type):
        """Iterate over all messages of a given type.

        The message_type parameter must be one of info, warning or error and
        those messages will be returned in the order they were added to the
        Repository.

        Args:
            message_type (str): The type of message that you want to iterate
                over.  One of "info", "warning", or "error".

        Returns:
            iterable of Message: An iterable of Message objects.
        """

        if message_type not in ('info', 'warning', 'error'):
            raise InternalError("Invalid message type '%s' given to iter_messages" % message_type)

        for msg in self._messages:
            if msg.type == message_type:
                yield msg

    def count_messages(self, message_type):
        """Count how many messages of a given type there are.

        Args:
            message_type (str): The type of message that you want to iterate
                over.  One of "info", "warning", or "error".

        Returns:
            int: The number of messages of the given type.
        """

        messages = list(self.iter_messages(message_type))
        return len(messages)

    def add_subsystem(self, subsystem):
        """Add a subsystem to this repository."""
        self.subsystems.append(subsystem)

    def required_secret(self, name, subsystem, usage, verify=None, context="all"):
        """Add a required environment variable.

        See the documentation for Repository.add_secret().
        """

        self.add_secret(name, subsystem, usage, required=True, verify=verify, context=context)

    def optional_secret(self, name, subsystem, usage, verify=None, context="all"):
        """Add an optional environment variable.

        See the documentation for Repository.add_secret().
        """

        self.add_secret(name, subsystem, usage, required=False, verify=verify, context=context)

    def add_secret(self, name, subsystem, usage, required, verify=None, context="all"):
        """Add an optional or required environment variable.

        Environment variables are needed when Repository.update() is called
        and are used to convey secret information that must be encrypted and
        stored in the repository itself.  The way this information is used
        and what specific environment variables are required is 100% decided
        by the RepositoryTemplate that is managing the repository.

        This method exists for the RepositoryTemplate to convey to the
        Repository class what environment variables it needs and whether they
        are required or optional.  If the relevant subsystem has a method
        of verifying the contents of the environment variable, it can also
        pass a callable function in the verify parameter that will be used
        to verify the value of the environment variable.

        This method can be called multiple times with the same ``name``
        parameter by different subsystems if they both use the same
        enviornment variable.

        The context parameter must be a comma separated list with each entry
        being one of "update", "all", "build", "deploy".  The context
        parameter controls when an environment variable is needed.  It is used
        to get lists of all environment variables that might be needed during,
        e.g. building or deploying a project.  Only variables marked for a
        given context are provided when that context runs.

        Args:
            name (str): The name of the environment variable
            subsystem (str): The name of the subsystem that needs the variable
            usage (str): A short, one line description of how the variable is
                used by the subsystem.
            required (bool): Whether the variable is optional or required.
            verify (callable): Optional callable with signature:
                callable(name, value) that is called with the name and value
                of the environment variable as strings and should return None
                if the variable is valid.  If the variable is invalid, it
                should return a ``str`` instance with a short message
                describing why the variable's contents are not valid.
            context (list of str): A comma separated list of contexts during
                which this environment variable is needed.  Supported contexts
                are update, all, build an deploy.
        """

        context_list = [x.strip() for x in context.split(',')]
        for context_entry in context_list:
            if context_entry not in ('all', 'build', 'deploy', 'update'):
                raise InternalError("Invalid context specified in add_env_variable: '%s' as part of '%s'" % (context_entry, context))

        contexts = set(context_list)
        if "all" in contexts:
            contexts.remove("all")
            contexts.update(['build', 'deploy', 'update'])

        env = EnvironmentVariable(name, subsystem, contexts, usage, required, verify)
        if name not in self._env_variables:
            self._env_variables[name] = []

        self._env_variables[name].append(env)

    def iter_secrets(self):
        """Iterate over all declared secrets."""

        for var_name in sorted(self._env_variables):
            yield var_name, self._env_variables[var_name], os.environ.get(var_name)

    def get_secret(self, name):
        """Get the value of a secret from the user's environment.

        If the secret is marked as required and it is not present, an
        exception is raised, otherwise None is returned when the value
        is not present.

        Args:
            name (str): The name of the secret that was previously registered
                with add_secret(), required_secret(), or optional_secret().

        Returns:
            str: The secret's value or None if it is optional and not present.

        Raises:
            InvalidEnvironmentError: If the secret is required and not present.
            IntenalError: If ``name`` was never declared as a secret.
        """

        var_entries = self._env_variables.get(name)
        if var_entries is None:
            raise InternalError("Cannot find secret declaration '%s' in get_secret()" % name)

        required = False
        found_entry = None
        for var_entry in var_entries:
            if var_entry.required:
                required = True
                found_entry = var_entry

        value = os.environ.get(name)
        if value is None and required:
            raise InvalidEnvironmentError(name, found_entry.usage)

        return value

    def iter_context(self, context, include_empty=True):
        """Iterate over environment variables applicable to a given context.

        The `context` parameter must be one of 'update', 'build', or 'deploy'
        and will be used to select environment variables needed in that
        context.

        The variables will be yielded in sorted order by name for consistency.

        Args:
            context (str): The context we wish to get variables for.  Must
                be one of update, build or deploy.  Variables marked with
                all will be returned for all contexts.
            include_empty (bool): Also yield None for optional environement
                variables that are not defined in the user's ENVIRONMENT.

        Returns:
            iterable of str, str: An iterable of variable name and value.

            Each variable that is marked with the passed context will be
            returned as part of the iterable in stable sorted order.  If the
            variable is marked as optional and it is not defined in the
            process's environment, then a None value will be yielded if
            include_empty is True (the default behvaior), otherwise the
            variable will be skipped as if it were not declared at all.
        """

        known_contexts = frozenset(['update', 'build', 'deploy'])
        if context not in known_contexts:
            raise InternalError("Unkown context %s in Repository.iter_environment" % context)

        for var_name in sorted(self._env_variables):
            found_entry = None
            required = False
            for var_entry in self._env_variables[var_name]:
                if context in var_entry.contexts:
                    if found_entry is None:
                        found_entry = var_entry

                    if var_entry.required:
                        required = True

            if found_entry is None:
                continue

            value = os.environ.get(var_name)
            if value is None and required:
                raise InvalidEnvironmentError(var_name, found_entry.usage)
            elif value is None and not include_empty:
                continue

            yield var_name, value

    def _load_settings(self, settings):
        """Load and validate settings dictionary."""

        version = settings.get('version')
        if version is None:
            self.error(self.SETTINGS_FILE, "Missing required version key",
                       "Run `multipackage init --force` or manually fix.")

        # FIXME: The template class should handle checking for outdated versions
        if version != self.SETTINGS_VERSION:
            self.warning(self.SETTINGS_FILE, "Old file version ({})".format(version),
                         "Run `multipackage update`")

        self.author = settings.get('author', "Unknown Author")
        self.name = settings.get('name', "Unknown Project")

        self.options = settings.get('options', {})
        return settings.get('template', self.DEFAULT_TEMPLATE)

    def get_setting(self, name, default=_MISSING):
        """Get the value of a setting from the options dictionary.

        The name of the setting can be a series of dot separated identifiers
        that will be resolved recursively into subkeys.

        For example, "doc.deploy" would be the key "deploy" in a dictionary
        assigned to the key "doc".  "doc" would return the entire doc
        dictionary.

        Args:
            name (str): The name of the setting that we want to fetch.
            default (object): If the setting is optional, you can specify
                a default value.  The default behavior is to raise an
                exception when a setting is missing.

        Returns:
            str: The value of the setting.
        """

        if '.' in name:
            names = name.split('.')
        else:
            names = [name]

        curr = self.options
        value = default

        for component in names[:-1]:
            if not isinstance(curr, dict):
                break

            if component not in curr:
                break

            curr = curr[component]

        component = names[-1]
        if isinstance(curr, dict) and component in curr:
            value = curr[component]

        if value is _MISSING:
            raise InvalidSettingError(name, "Missing required key in settings dictionary")

        return value

    def set_setting(self, name, value):
        """Change or set an option in settings.json.

        The change is flushed out to the settings file immediately.

        Args:
            name (str): The name of the setting you want to set or change.
            value (object): A json serializable value.
        """

        if '.' in name:
            names = name.split('.')
        else:
            names = [name]

        curr = self.options

        for i, component in enumerate(names[:-1]):
            if not isinstance(curr, dict):
                subname = ".".join(names[:i])
                raise InvalidSettingError(name, "Cannot set key %s because subkey %s exists and is not a dictionary" % (name, subname))

            if component not in curr:
                curr[component] = {}

            curr = curr[component]

        component = names[-1]
        if not isinstance(curr, dict):
            subname = ".".join(names[:-1])
            raise InvalidSettingError(name, "Cannot set key %s because subkey %s exists and is not a dictionary" % (name, subname))

        curr[component] = value

        out_path = os.path.join(self.path, self.SETTINGS_FILE)

        self._original_settings['options'] = self.options
        atomic_json(out_path, self._original_settings)
        self.manifest.update_file(out_path, hash_type="json")

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

    def ensure_template(self, relative_path, template, variables=None, present=True, overwrite=True, raw=False, filters=None):
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
            filters (dict): Optional dictionary of callable filters that will be passed
                to jinja2 for use in the template formatting.
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

            render_template(template, variables, out_path=path, filters=filters)

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
