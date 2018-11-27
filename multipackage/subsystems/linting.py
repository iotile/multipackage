"""Linting subsystem that ensures we have pylint support."""

import logging

class LintingSubsystem:
    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

    def update(self, options):
        """Update the linting subsystem."""

        self._repo.ensure_lines("requirements_test.txt", ["pylint"])
        self._repo.ensure_template(".pylintrc", template="pylintrc")
