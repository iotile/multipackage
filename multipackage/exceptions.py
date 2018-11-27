"""Internal exceptions that multipackage might throw."""

from __future__ import unicode_literals


class UsageError(Exception):
    """Raised when a multipackage API method is called incorrectly."""

    def __init__(self, message, suggestion=None):
        super(UsageError, self).__init__(message)

        self.message = message
        self.suggestion = suggestion


class InvalidEnvironmentError(Exception):
    """Raised when a required environment variable is not present."""

    def __init__(self, variable_name, reason, suggestion=None):
        super(InvalidEnvironmentError, self).__init__("Missing environment variable {}".format(variable_name))

        self.variable_name = variable_name
        self.reason = reason
        self.suggestion = suggestion


class MissingPackageError(Exception):
    """Raised when a required support package is not present."""

    def __init__(self, package_name, reason):
        super(MissingPackageError, self).__init__("Missing package {}".format(package_name))

        self.package_name = package_name
        self.reason = reason


class InvalidPackageError(Exception):
    """Raised when a required support package has an invalid version."""

    def __init__(self, package_name, version, required_version, reason):
        super(InvalidPackageError, self).__init__("Python package {} has unsupported version {}, requires {}".format(package_name, version, required_version))

        self.package_name = package_name
        self.reason = reason
        self.actual_version = version
        self.required_version = required_version


class ManualInterventionError(Exception):
    """Raised when there is a situation that requires manual intervention."""

    def __init__(self, message, path=None):
        super(ManualInterventionError, self).__init__("Manual intervention required: {}, path={}".format(message, path))

        self.message = message
        self.path = path


class InternalError(Exception):
    """An internal error has occurred."""

    def __init__(self, reason, suggestion=None):
        super(InternalError, self).__init__("Internal error occurred: {}".format(reason))

        self.reason = reason
        self.suggestion = suggestion
