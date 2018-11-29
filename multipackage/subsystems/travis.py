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
        env = {
            'github_token': self._travis.encrypt_env(slug, "GITHUB_TOKEN"),
            'pypi_user': self._travis.encrypt_env(slug, "PYPI_USER"),
            'pypi_pass': self._travis.encrypt_env(slug, "PYPI_PASS"),
            'slack_token': self._travis.encrypt_env(slug, "SLACK_TOKEN", only_value=True),
            'slack_web_hook': self._travis.encrypt_env(slug, "SLACK_WEB_HOOK")
        }

        variables = {
            'options': options,
            'components': self._repo.components,
            'env': env
        }

        self._repo.ensure_template(".travis.yml", "travis.yml.tpl", variables)
