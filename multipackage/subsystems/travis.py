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

        slug = self._repo.github_slug()

        # See https://github.com/travis-ci/travis-ci/issues/9548
        # we need to encrypt all environment variables together rather than
        # separately with a list.
        variables = {
            'options': options,
            'components': self._repo.components,
            'deploy_tokens': self._travis.encrypt_env(slug, "GITHUB_TOKEN")
        }

        self._repo.ensure_template(".travis.yml", "travis.yml.tpl", variables)
