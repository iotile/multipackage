"""A best-practices template for distributing python packages on PyPI."""

import os
import logging
from .repo_template import RepositoryTemplate
from .. import subsystems
from ..utilities import find_toplevel_packages
from ..exceptions import InternalError


class PyPIPackageTemplate(RepositoryTemplate):
    SHORT_NAME = "pypi_package"
    SHORT_DESCRIPTION = "Builds, tests and releases PyPI packages from Travis-CI"
    INFO_TEMPLATE = "pypi_info_template.tpl"
    DOCTOR_TEMPLATE = "pypi_doctor_template.tpl"

    def __init__(self):
        super(PyPIPackageTemplate, self).__init__()
        self.namespace_packages = []
        self.desired_packages = {}
        self.toplevel_packages = {}

        self._logger = logging.getLogger(__name__)

    def install(self, repo):
        """Install this template into a Repository.

        Args:
            repo (Repository): The repository that this template should add
                its subsystems to.
        """

        self._verify_options(repo)
        self._find_packages(repo)

        repo.add_subsystem(subsystems.BasicPythonSupport(repo))
        repo.add_subsystem(subsystems.PylintLinter(repo))
        repo.add_subsystem(subsystems.TravisSubsystem(repo))
        repo.add_subsystem(subsystems.SphinxDocumentation(repo, self.desired_packages,
                           self.toplevel_packages, namespace_packages=self.namespace_packages))

    @classmethod
    def _verify_options(cls, repo):
        for key, comp in repo.components.items():
            for name, value in comp.options.items():
                if name == 'compatibility' and value not in ('universal', 'python2', 'python3'):
                    repo.error(".multipackage/components.txt",
                                   "Invalid compatibility option for component %s: %s" % (key, value),
                                   "Choices are universal, python2 or python3")

    def _find_packages(self, repo):
        self.toplevel_packages = self.find_toplevel_packages(repo.path, repo.components)
        self.namespace_packages = self.find_namespace_packages(self.toplevel_packages)

        if len(self.namespace_packages) == 0:
            self.desired_packages = self.toplevel_packages
        else:
            self._logger.info("Found namespace packages: %s, pruning them", ", ".join(self.namespace_packages))
            self.desired_packages = self.find_toplevel_packages(repo.path, repo.components, self.namespace_packages)

    @classmethod
    def find_toplevel_packages(cls, base_path, components, prefixes=None):
        """Find all top level python packages in each component."""

        packages = {}

        for key, comp in components.items():
            path = os.path.join(base_path, comp.relative_path)
            toplevel_packages = find_toplevel_packages(path)

            if prefixes is not None:
                if len(toplevel_packages) != 1:
                    raise InternalError("Cannot support multiple packages per component in '%s' if there is a namespace package" % key)

                if toplevel_packages[0] in prefixes:
                    toplevel_packages = find_toplevel_packages(path, prefix=toplevel_packages[0])

            packages[key] = toplevel_packages

        return packages

    @classmethod
    def find_namespace_packages(cls, packages):
        """Find packages that are created by multiple components."""

        namespace_packages = set()
        seen_packages = set()

        for toplevel_packages in packages.values():
            for package in toplevel_packages:
                if package in seen_packages:
                    namespace_packages.add(package)
                else:
                    seen_packages.add(package)

        namespace_packages = sorted(namespace_packages)
        return namespace_packages
