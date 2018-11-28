"""Documentation subsystem that manages autogenerating documentation."""

import logging
from ..exceptions import InternalError

class DocumentationSubsystem:
    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

    def update(self, options):
        """Update the documentation subsystem."""

        # Make sure we pin all of our versions
        self._repo.ensure_lines("requirements_doc.txt",
                                ["sphinx", "jinja2", "sphinx_rtd_theme", "sphinxcontrib-programoutput",
                                 "recommonmark"], present=False)

        self._repo.ensure_lines("requirements_doc.txt",
                                ["sphinx ~= 1.8", "jinja2 ~= 2.10", "sphinx_rtd_theme ~= 0.4", "sphinxcontrib-programoutput ~= 0.11",
                                 "recommonmark ~= 0.4"])

        self._repo.ensure_lines(".gitignore", ['.tmp_docs', 'built_docs'])

        self._repo.ensure_directory("doc")
        self._repo.ensure_directory("doc/_static", gitkeep=True)
        self._repo.ensure_directory("doc/_template", gitkeep=True)
        self._repo.ensure_directory("built_docs", gitkeep=True)

        namespace_package = None
        if len(self._repo.namespace_packages) > 1:
            raise InternalError("Having more than one namespace package is not yet supported: %s" % self._repo.namespace_packages)
        elif len(self._repo.namespace_packages):
            namespace_package = self._repo.namespace_packages[0]

        variables = {
            'options': options,
            'components': self._repo.components,
            'doc': options.get('documentation', {}),
            'namespace': namespace_package
        }

        self._repo.ensure_template("doc/_template/module.rst", template="module.rst", raw=True)
        self._repo.ensure_template("doc/_template/package.rst", template="package.rst", raw=True)

        # Install our basic rst sphinx index files
        self._repo.ensure_template("doc/conf.py", "conf.py.tpl", variables)
        self._repo.ensure_template("doc/index.rst", "index.rst.tpl", variables, overwrite=False)
        self._repo.ensure_template("doc/api.rst", "api.rst.tpl", variables)
        self._repo.ensure_template("doc/release.rst", "release.rst.tpl", variables)

        # Install the documentation building scripts
        self._repo.ensure_script("scripts/generate_api.py", "generate_api.py")
        self._repo.ensure_script("scripts/better_apidocs.py", "better_apidocs.py")
        self._repo.ensure_template("scripts/build_documentation.py", "build_documentation.py.tpl", variables)
