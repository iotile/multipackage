"""Basic files like editor settings and gitignore."""

import logging

class BasicSubsystem:
    """Basic managed files."""

    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

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
            "requests",
            "twine ~= 1.12",
            "pycryptodome",
            "pytest ~= 4.0",
            "wheel"
        ])

        variables = {
            'options': options,
            'components': self._repo.components,
            'doc': options.get('documentation', {}),
        }

        self._repo.ensure_directory("scripts")
        self._repo.ensure_template("scripts/components.txt", template="components.txt", overwrite=False)
        self._repo.ensure_template("scripts/release_by_name.py", "release_by_name.py.tpl", variables)

        self._repo.ensure_script("scripts/release_component.py", "release_component.py")
