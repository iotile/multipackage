"""Linting subsystem that ensures we have pylint support."""

import logging

class LintingSubsystem:
    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

    def update(self, options):
        """Update the linting subsystem."""

        linting = options.get('linting', {})
        enabled = linting.get('enabled', True)

        self._repo.ensure_lines("requirements_build.txt", ["pylint"], present=enabled)
        self._repo.ensure_template(".pylintrc", template="pylintrc", present=enabled)
