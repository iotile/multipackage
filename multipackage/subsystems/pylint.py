"""Linting subsystem that ensures we have pylint support."""

import logging

class PylintLinter(object):
    SHORT_NAME = "Linting with pylint"
    SHORT_DESCRIPTION = "checks for linting violations using best-practices .pylintrc settings"

    def __init__(self, repo, pylintrc_template="pylintrc"):
        self._repo = repo
        self._pylintrc_template = pylintrc_template
        self._logger = logging.getLogger(__name__)

    def update(self, options):
        """Update the linting subsystem."""

        linting = options.get('linting', {})
        enabled = linting.get('enabled', True)

        self._repo.ensure_lines("requirements_build.txt", ['pylint ~= 1.9'],
                                [r"^pylint"], present=enabled)
        self._repo.ensure_template(".pylintrc", template=self._pylintrc_template, present=enabled)
