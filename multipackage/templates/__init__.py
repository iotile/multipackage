"""Templates for different types of repository.

Templates are the primary way that you can configure how multipackage manages
a repository.  Every repository has a template (possibly configured explicitly
and possibly using the default template for PyPI distributed open-source
packages).

A template determines which Subsystems are added to the Repository class.
A subsystem actually manages some aspect of a given repository.  For example,
the default ``pypi_package`` template has the following subsystems:

- BasicSubsystem
- DocumentationSubsystem
- LintingSubsystem
- TravisSubsystem

Each subsystem determines what environment variables it supports for
configuring secure credentials when ``multipackage update`` is called.

So the overall structure is:

A Repository has a Template that selects Subsystems.  The selected Subsystems
determine what actions are taken on the repository and what environment
variables are required and optional.
"""

from .repo_template import RepositoryTemplate
from .pypi_package import PyPIPackageTemplate

__all__ = ['RepositoryTemplate', 'PyPIPackageTemplate']
