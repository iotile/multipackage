"""Add support for automatic testing and deployment from Travis CI."""

import logging
from ..travis import TravisCI

class TravisSubsystem:
    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)
        self._travis = TravisCI()

    def update(self, options):
        """Update the linting subsystem."""

        variables = {
            'options': options
        }

        self._repo.ensure_template(".travis.yml", "travis.yml.tpl", variables)
