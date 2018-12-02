"""Documentation subsystem that manages autogenerating documentation."""

import logging
import os
from ..exceptions import InternalError

class SphinxDocumentation(object):
    SHORT_NAME = "Sphinx documentation"
    SHORT_DESCRIPTION = "generates and deploys api reference and prose documentation using sphinx"
    def __init__(self, repo, desired_packages, toplevel_packages=None, namespace_packages=None):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

        if namespace_packages is None:
            namespace_packages = []

        if toplevel_packages is None:
            toplevel_packages = desired_packages

        self._namespace_packages = namespace_packages
        self._desired_packages = desired_packages
        self._toplevel_packages = toplevel_packages

    def update(self, options):
        """Update the documentation subsystem."""

        # Make sure we pin all of our versions
        self._repo.ensure_lines("requirements_doc.txt",
                                ["sphinx ~= 1.8", "jinja2 ~= 2.10", "sphinx_rtd_theme ~= 0.4", "sphinxcontrib-programoutput ~= 0.11", "recommonmark ~= 0.4"],
                                [r"^sphinx", r"^jinja2", r"^sphinx_rtd_theme", r"^sphinxcontrib-programoutput", r"^recommonmark"],
                                multi=True)

        self._repo.ensure_lines(".gitignore", ['.tmp_docs', 'built_docs'])

        self._repo.ensure_directory("doc")
        self._repo.ensure_directory("doc/_static", gitkeep=True)
        self._repo.ensure_directory("doc/_template", gitkeep=True)
        self._repo.ensure_directory("built_docs", gitkeep=True)

        namespace_package = None
        if len(self._namespace_packages) > 1:
            raise InternalError("Having more than one namespace package is not yet supported: %s" % self._repo.namespace_packages)
        elif len(self._namespace_packages) == 1:
            namespace_package = self._namespace_packages[0]

        variables = {
            'options': options,
            'components': self._repo.components,
            'doc': options.get('documentation', {}),
            'repo': self._repo,
            'namespace': namespace_package,
            'desired_packages': self._desired_packages,
            'toplevel_packages': self._toplevel_packages
        }

        self._repo.ensure_template("doc/_template/module.rst", template="module.rst", raw=True)
        self._repo.ensure_template("doc/_template/package.rst", template="package.rst", raw=True)

        # Install our basic rst sphinx index files
        self._repo.ensure_template("doc/conf.py", "conf.py.tpl", variables)
        self._repo.ensure_template("doc/index.rst", "index.rst.tpl", variables, overwrite=False)
        self._repo.ensure_template("doc/api.rst", "api.rst.tpl", variables)
        self._repo.ensure_template("doc/release.rst", "release.rst.tpl", variables)

        # Install the documentation building scripts
        self._repo.ensure_script(os.path.join(self._repo.SCRIPT_DIR, "generate_api.py"), "generate_api.py")
        self._repo.ensure_script(os.path.join(self._repo.SCRIPT_DIR, "better_apidocs.py"), "better_apidocs.py")
        self._repo.ensure_template(os.path.join(self._repo.SCRIPT_DIR, "build_documentation.py"), "build_documentation.py.tpl", variables)
