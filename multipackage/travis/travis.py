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

    Note that repositories can run builds on either travis-ci.org or travis-ci.com.
    When encrypting environment variables, it's required that the variable be
    encrypted with the public key for either .com or .org, otherwise the variable
    will not decrypt correctly.

    You must have environment variables set for:

      - TRAVIS_TOKEN_COM: Your travis-ci.com token
      - TRAVIS_TOKEN_ORG: YOur travis-ci.org token

    Args:
        com_token (str): Optional API token for travis-ci.com.  If not
            specified it is read from the environment variables
            TRAVIS_TOKEN_COM. If the environment variable is not specified, an
            exception is raised.
        org_token (str): Optional API token for travis-ci.org.  If not
            specified it is read from the environment variables
            TRAVIS_TOKEN_ORG. If the environment variable is not specified, an
            exception is raised.
    """

    TRAVIS_BASE_COM = "https://api.travis-ci.com"
    TRAVIS_BASE_ORG = "https://api.travis-ci.org"

    NO_ENV_REASON = "Needed to authenticate to the Travis CI API"
    INVALID_REASON = "You have a token but it was rejected by Travis"
    SUGGESTION_COM = "Your travis-ci.COM token is on the settings tab of your travis-ci profile: https://travis-ci.com/account/preferences"
    SUGGESTION_ORG = "Your travis-ci.ORG token is on the settings tab of your travis-ci profile: https://travis-ci.org/account/preferences"

    _key_cache = {}

    def __init__(self, com_token=None, org_token=None):
        if com_token is None:
            com_token = os.environ.get("TRAVIS_TOKEN_COM")
        if org_token is None:
            org_token = os.environ.get("TRAVIS_TOKEN_ORG")

        if com_token is None:
            raise InvalidEnvironmentError("TRAVIS_TOKEN_COM", TravisCI.NO_ENV_REASON, TravisCI.SUGGESTION_COM)

        if com_token is None:
            raise InvalidEnvironmentError("TRAVIS_TOKEN_ORG", TravisCI.NO_ENV_REASON, TravisCI.SUGGESTION_ORG)

        if os.environ.get("TRAVIS_ORG_URL") is not None:
            self.TRAVIS_BASE_ORG = os.environ.get("TRAVIS_ORG_URL")

        if os.environ.get("TRAVIS_COM_URL") is not None:
            self.TRAVIS_BASE_COM = os.environ.get("TRAVIS_COM_URL")

        self._com_token = com_token
        self._org_token = org_token
        self._logger = logging.getLogger(__name__)

    def _get(self, url, org=False):
        if org:
            base = self.TRAVIS_BASE_ORG
            token = self._org_token
        else:
            base = self.TRAVIS_BASE_COM
            token = self._com_token

        headers = {"Authorization": 'token {}'.format(token),
                   "Travis-API-Version": "3"}

        if not url.startswith('/'):
            url = "/" + url

        resource = base + url

        self._logger.debug("HTTP GET %s", resource)
        resp = requests.get(resource, headers=headers)
        self._logger.debug("HTTP RESPONSE: %s", resp)

        return resp

    def _get_parse(self, url, org=False):
        resp = self._get(url, org=org)

        if resp.status_code >= 200 and resp.status_code < 300:
            return resp.json()

        raise InternalError("Could not access URL {}, error code {}".format(url, resp.status_code),
                            "Make sure the API endpoint exists")

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

    def use_travis_org(self, repo_slug):
        """Check and see if this repo is on travis.org or com.

        Returns:
            bool: True if on travis-ci.org, False if on travis-ci.com.
        """

        encoded_slug = self._encode_repo_slug(repo_slug)

        try:
            resp = self._get_parse("repo/{}".format(encoded_slug), org=False)
            return resp.get('active_on_org', False)
        except:
            pass

        try:
            resp = self._get_parse("repo/{}".format(encoded_slug), org=True)
            return resp.get('active_on_org', False)
        except:
            pass

        raise InternalError("Could not find repository %s on either travis-ci.org or travis-ci.com" % encoded_slug)

    def get_key(self, repo_slug):
        """Get the encryption key for a repository by its slug.

        This method will automatically get the correct key for the repository
        whether it is running on travis-ci.com or travis-ci.org.  It will only
        look up each key once using a global cache of keys.
        """

        if repo_slug in self._key_cache:
            self._logger.debug("Using cached key for repository %s", repo_slug)
            return self._key_cache[repo_slug]

        org = self.use_travis_org(repo_slug)
        if org:
            self._logger.info("Getting encryption key for %s on travis-ci.org", repo_slug)
        else:
            self._logger.info("Getting encryption key for %s on travis-ci.com", repo_slug)

        encoded_slug = self._encode_repo_slug(repo_slug)

        resp = self._get_parse("repo/{}/key_pair/generated".format(encoded_slug), org=org)

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

    def encrypt_env(self, repo_slug, *env_names, **kwargs):
        """Encrypt one or more environment variables.

        The resulting string is suitable for pasting directly into a
        .travis.yml file, i.e. it is of the form secure: <encrypted value>

        See https://github.com/travis-ci/travis-ci/issues/9548 for why it
        could be necessary to include all secure environment variables in a
        single line.

        If only value is passed as a keyword arg, you must give a single
        environment variable name and its raw value will be encrypted without
        a NAME= prefix.
        """

        only_value = kwargs.get('only_value', False)

        if only_value and len(env_names) != 1:
            raise InternalError("TravisCI.encrypt_env called with multiple variables and only_value=True")

        raw_vals = []

        for env_name in env_names:
            env_value = os.environ.get(env_name)
            if env_value is None:
                raise InvalidEnvironmentError(env_name, "Needed to store as encrypted environment variable",
                                              "Make sure your environment variables are set correctly")

            raw_vals.append(env_value)

        if only_value:
            enc_text = self.encrypt_string(repo_slug, raw_vals[0])
        else:
            raw_envs = ["{}={}".format(name, value) for name, value in zip(env_names, raw_vals)]
            raw_txt = " ".join(raw_envs)

            enc_text = self.encrypt_string(repo_slug, raw_txt)

        return "secure: {}".format(enc_text)
