"""Wrapper class for Travis CI API v3."""

from __future__ import unicode_literals
import os
import sys
import logging

try:
    from urllib import quote  # Python 2.X
except ImportError:
    from urllib.parse import quote  # Python 3+

import requests
import base64
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from ..exceptions import InvalidEnvironmentError, InternalError


class TravisCI:
    """Wrapper for Travis CI API v3.

    This wrapper is not complete but currently just implements the features
    needed for multipackage including setting up a repository and encrypting
    data.

    Args:
        token (str): Optional Travis CI token.  If not specified it is read
            from the environment variable TRAVIS_TOKEN.  If the environment
            variable is not specified, an exception is raised.
    """

    TRAVIS_BASE = "https://api.travis-ci.org"

    NO_ENV_REASON = "Needed to authenticate to the Travis CI API"
    INVALID_REASON = "You have a token but it was rejected by Travis"
    SUGGESTION = "Your token is on the settings tab of your travis-ci profile: https://travis-ci.org/account/preferences"

    _key_cache = {}

    def __init__(self, token=None):
        if token is None:
            token = os.environ.get("TRAVIS_TOKEN")
            if token is None:
                raise InvalidEnvironmentError("TRAVIS_TOKEN", TravisCI.NO_ENV_REASON, TravisCI.SUGGESTION)

        self.token = token
        self._logger = logging.getLogger(__name__)

    def _get(self, url):
        headers = {"Authorization": 'token {}'.format(self.token),
                   "Travis-API-Version": "3"}

        if not url.startswith('/'):
            url = "/" + url

        resource = self.TRAVIS_BASE + url

        self._logger.debug("HTTP GET %s", resource)
        resp = requests.get(resource, headers=headers)
        self._logger.debug("HTTP RESPONSE: %s", resp)

        return resp

    def _get_parse(self, url):
        resp = self._get(url)

        if resp.status_code >= 200 and resp.status_code < 300:
            return resp.json()

        raise InternalError("Could not access URL {}, error code {}".format(url, resp.status_code),
                            "Make sure the API endpoint exists")

    def ensure_token(self):
        """Ensure that the Travis CI access token is valid."""

        resp = self._get('user')
        if resp.status_code >= 200 and resp.status_code < 300:
            return

        self._logger.error("Token check failed, response: %s, content=%s", resp, resp.text)
        raise InvalidEnvironmentError("TRAVIS_TOKEN", self.INVALID_REASON, self.SUGGESTION)

    def _encode_repo_slug(self, repo_slug):
        # Allow (org, repository) format for repo_slug
        if isinstance(repo_slug, tuple):
            repo_slug = "/".join(repo_slug)

        return quote(repo_slug, safe='')

    def get_info(self, repo_slug):
        """Get info about this repository on Travis CI.

        Args:
            repo_slug (str): The repository slug to set up.

        Returns:
            dict: The repository info
        """

        encoded_slug = self._encode_repo_slug(repo_slug)
        info = self._get_parse("repo/{}".format(encoded_slug))

        self._logger.debug("Repository info on %s: %s", repo_slug, info)
        return info

    def get_key(self, repo_slug):
        """Get the encryption key for a repository by its slug."""

        encoded_slug = self._encode_repo_slug(repo_slug)

        resp = self._get_parse("repo/{}/key_pair/generated".format(encoded_slug))

        key = resp.get('public_key')
        if resp is None:
            self._logger.error("Unknown response from Travis CI in get_key: %s", resp)
            raise InternalError("Unknown response from Travis-CI API: {}".format(resp),
                                "Check the API documentation")

        key = key.replace('\\n', '\n')
        self._key_cache[repo_slug] = key

        return key

    def encrypt_string(self, repo_slug, text):
        """Encrypt a string using the repo's public key."""

        self._logger.debug("Encrypting '%s' for repo '%s'", text, repo_slug)

        if not isinstance(text, bytes):
            text = text.encode('utf-8')

        key_data = self.get_key(repo_slug)
        key = RSA.importKey(key_data)

        cipher = PKCS1_v1_5.new(key)
        ciphertext = cipher.encrypt(text)

        return base64.b64encode(ciphertext).decode('utf-8')

    def encrypt_env(self, repo_slug, *env_names):
        """Encrypt one or more environment variables.

        The resulting string is suitable for pasting directly into a
        .travis.yml file, i.e. it is of the form secure: <encrypted value>

        See https://github.com/travis-ci/travis-ci/issues/9548 for why it
        is necessary to include all secure environment variables in a
        single line.
        """

        raw_envs = []

        for env_name in env_names:
            env_value = os.environ.get(env_name)
            if env_value is None:
                raise InvalidEnvironmentError(env_name, "Needed to store as encrypted environment variable",
                                              "Make sure your environment variables are set correctly")

            raw_txt = '{}="{}"'.format(env_name, env_value)
            raw_envs.append(raw_txt)

        raw_txt = " ".join(raw_envs)

        enc_text = self.encrypt_string(repo_slug, raw_txt)

        return "secure: {}".format(enc_text)
