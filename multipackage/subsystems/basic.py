"""Basic files like editor settings and gitignore."""

import logging
import os

class BasicPythonSupport(object):
    """Basic managed files for python based repositories."""

    SHORT_NAME = "Basic python support"
    SHORT_DESCRIPTION = "pypi release scripts, editorconfig and build requirements"

    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

        repo.required_secret('PYPI_USER', self.SHORT_NAME,
                             'Username for uploading packages to the target PyPI Index',
                             context="deploy")
        repo.required_secret('PYPI_PASS', self.SHORT_NAME,
                             'Password for uploading packages to the target PyPI Index',
                             context="deploy")

        repo.optional_secret('PYPI_URL', self.SHORT_NAME,
                             'URL of a custom PyPI index that we should release to',
                             context="deploy")

    def update(self, options):
        """Update the basic subsystem."""

        self._repo.ensure_lines(".gitignore", [
            "workspace/",
            "*.egg-info/",
            "dist/*",
            "__pycache__",
            "*.pyc",
            ".pytest_cache/",
            "build/*"
        ])

        self._repo.ensure_template(".editorconfig", template="editorconfig")
        self._repo.ensure_lines("requirements_build.txt", [
            "requests ~= 2.20",
            "twine ~= 1.12",
            "pycryptodome ~= 3.7",
            "pytest ~= 4.0",
            "wheel >= 0.32"
        ], [
            r"^requests",
            r"^twine",
            r"^pycryptodome",
            r"^pytest",
            r"^wheel"
        ], multi=True)

        variables = {
            'options': options,
            'components': self._repo.components
        }

        self._repo.ensure_directory(self._repo.SCRIPT_DIR)
        self._repo.ensure_template(os.path.join(self._repo.MULTIPACKAGE_DIR, "components.txt"), template="components.txt", overwrite=False)
        self._repo.ensure_template(os.path.join(self._repo.SCRIPT_DIR, "release_by_name.py"), "release_by_name.py.tpl", variables)
        self._repo.ensure_template(os.path.join(self._repo.SCRIPT_DIR, "test_by_name.py"), "test_by_name.py.tpl", variables)
        self._repo.ensure_template(os.path.join(self._repo.SCRIPT_DIR, "components.py"), "components.py.tpl", variables)
        self._repo.ensure_template(os.path.join(self._repo.SCRIPT_DIR, "tag_release.py"), "tag_release.py.tpl", variables)

        self._repo.ensure_script(os.path.join(self._repo.SCRIPT_DIR, "shared_errors.py"), "shared_errors.py")
        self._repo.ensure_script(os.path.join(self._repo.SCRIPT_DIR, "release_notes.py"), "release_notes.py")
        self._repo.ensure_script(os.path.join(self._repo.SCRIPT_DIR, "release_component.py"), "release_component.py")
