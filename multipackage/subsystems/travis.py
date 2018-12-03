"""Add support for automatic testing and deployment from Travis CI."""

import logging
import os
from ..external import TravisCI
from ..utilities import GITRepository


class TravisSubsystem(object):
    SHORT_NAME = "Travis CI (Python Profile)"
    SHORT_DESCRIPTION = "manages .travis.yml file for building and deploying on Travis CI"

    def __init__(self, repo):
        self._repo = repo
        self._logger = logging.getLogger(__name__)

        repo.required_secret('TRAVIS_TOKEN_COM', self.SHORT_NAME,
                             'Travis CI API token used for projects hosted on travis-ci.com',
                             context="update")
        repo.required_secret('TRAVIS_TOKEN_ORG', self.SHORT_NAME,
                             'Travis CI API token used for projects hosted on travis-ci.org',
                             context="update")
        repo.required_secret('GITHUB_TOKEN', self.SHORT_NAME,
                             'Github Token used for deploying documentation to Github Pages',
                             context="deploy")

        repo.optional_secret('SLACK_TOKEN', self.SHORT_NAME,
                             'Slack Travis-App token if notifications on build pass/fail are desired',
                             context="all")
        repo.optional_secret('SLACK_WEB_HOOK', self.SHORT_NAME,
                             'Slack web hook URL if notifications on project release are desired',
                             context="deploy")

    def update(self, options):
        """Update the linting subsystem."""

        git = GITRepository(self._repo.path)
        travis = TravisCI()

        slug = git.github_slug()

        encryptor = lambda name, only_value=False: travis.encrypt_env(slug, name, only_value=only_value)

        filters = {
            'encrypt': encryptor
        }

        variables = {
            'options': options,
            'components': self._repo.components,
            'repo': self._repo
        }

        self._repo.ensure_template(".travis.yml", "travis.yml.tpl", variables, filters=filters)
