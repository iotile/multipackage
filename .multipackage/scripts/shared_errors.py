"""Shared exceptions among the various command line scripts installed here."""

from __future__ import absolute_import, division, print_function, unicode_literals


class MismatchError(Exception):
    def __init__(self, subsystem, expected, found):
        super(MismatchError, self).__init__()
        self.message = "Information mismatch in '%s', expected: '%s', found: '%s'" % (subsystem, expected, found)


class ExternalError(Exception):
    def __init__(self, service, message):
        super(ExternalError, self).__init__()

        self.message = message
        self.service = service


class InternalError(Exception):
    def __init__(self, message):
        super(InternalError, self).__init__()

        self.message = message


class GenericError(Exception):
    def __init__(self, message, return_value=1):
        super(GenericError, self).__init__()

        self.message = message
        self.return_value = return_value



def handle_exception(exception):
    """Helper function for handling exceptions raised in main."""

    print()

    if isinstance(exception, MismatchError):
        print("ERROR: There is a mismatch in required component information of the environment")
        print(exception.message)
        retval = 1
    elif isinstance(exception, InternalError):
        print("ERROR: An internal error has occurred.  This indicates a bug in this script.")
        print(exception.message)
        retval = 2
    elif isinstance(exception, ExternalError):
        print("ERROR: An external service failed")
        print("Service: %s" % exception.service)
        print(exception.message)
        retval = 3
    elif isinstance(exception, KeyboardInterrupt):
        print()
        print("ERROR: Interrupted by Ctrl-C")
        retval = 4
    elif isinstance(exception, GenericError):
        print("ERROR: %s" % exception.message)
        retval = exception.return_value
    else:
        print("ERROR: An unknown exception occurred")
        print(str(exception))

    print()

    return retval
