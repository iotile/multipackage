"""Documentation subsystem that manages autogenerating documentation."""

import logging

class DocumentationSubsystem:
    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

    def update(self, options):
        """Update the documentation subsystem."""

        self._repo.ensure_lines("requirements_doc.txt",
                                ["sphinx", "jinja2"])

        self._repo.ensure_lines(".gitignore", ['.tmp_docs'])

        self._repo.ensure_directory("doc")
        self._repo.ensure_directory("doc/_static", gitkeep=True)
        self._repo.ensure_directory("doc/_template", gitkeep=True)
        self._repo.ensure_directory("built_docs", gitkeep=True)

        self._repo.ensure_template("doc/_template/module.rst", template="module.rst")
        self._repo.ensure_template("doc/_template/package.rst", template="package.rst")
