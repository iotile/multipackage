"""Base class for all Repository Templates."""

class RepositoryTemplate(object):
    """Base class for all Repository Templates.

    This class is the base class that all repository templates must either
    inherit from or implement the same functionality as.  The main purpose of
    this class is the ``install`` method that adds its subsystems to a
    Repository object.
    """

    SHORT_NAME = None
    """A unique name for this repository that can be used in a multipackage settings.json file."""

    SHORT_DESCRIPTION = None
    """A required one-line description that describes what the template does."""

    INFO_TEMPLATE = None
    """The name of a jinja2 template that will be used to render the multipackge info results."""

    def __init__(self):
        pass

    def install(self, repo):
        """Install this template into a Repository object.

        This method should instantiate all of its subsystems and call
        ``repo.add_subsystem()`` for all of the subsystems that are part of this
        repository.  All RepositoryTemplate subclasses must override this
        method.

        Args:
            repo (Repository): The repository where we should install this template.
        """

        raise NotImplementedError()
