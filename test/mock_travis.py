"""A simple mock travis-ci.{org, com} api."""

from __future__ import absolute_import, division, print_function

import re
from collections import namedtuple

import os.path
import json
import datetime
import csv
import logging
import uuid
import struct
import itertools
from future.utils import viewitems


HAS_DEPENDENCIES = True
try:
    import pytest
    from pytest_localserver.http import WSGIServer
    from werkzeug.wrappers import Request, Response
    import Crypto.PublicKey
except ImportError:
    HAS_DEPENDENCIES = False

# A preencoded response that should override any encoding handling in __call__()
EncodedResponse = namedtuple("EncodedResponse", ['encoding', 'data'])


class ErrorCode(Exception):
    def __init__(self, code):
        super(ErrorCode, self).__init__()
        self.status = code


class JSONErrorCode(Exception):
    """A non 200 response with JSON data."""

    def __init__(self, data, code):
        super(ErrorCode, self.__init__())

        self.status = code
        self.data = data


class MockTravisCI:
    """A test instance of the Travis-CI for continuous integration."""


    def __init__(self, ):
        if not HAS_DEPENDENCIES:
            raise RuntimeError("You must have pytest and pytest_localserver installed to be able to use MockIOTileCloud")

        self.logger = logging.getLogger(__name__)

        self.reset()

        self.com_key = Crypto.PublicKey.RSA.generate(2048)
        self.org_key = Crypto.PublicKey.RSA.generate(2048)

        self.apis = []
        self._add_api(r"/repo/([a-zA-Z0-9_\-%]+/[a-zA-Z0-9_\-%]+)/key_pair/generated", self.get_public_key)
        self._add_api(r"/repo/([a-zA-Z0-9_\-%]+/[a-zA-Z0-9_\-%]+)$", self.get_repo)

    def reset(self):
        """Clear any stored data in in this cloud as if we created a new instance."""

        self.request_count = 0
        self.error_count = 0

        self.org_projects = {}
        self.com_projects = {}

        self.quick_add_project('org/my_package', server="org")
        self.quick_add_project('com/my_package', server="com")

    def get_repo(self, request, repo_slug):
        """/repo/{slug} endpoint."""

        server = self.verify_token(request)

        self.logger.info("get_repo called with %s on server:%s", repo_slug, server)

        if server == "com":
            repo = self.com_projects.get(repo_slug)
        else:
            repo = self.org_projects.get(repo_slug)

        if repo is None:
            raise ErrorCode(404)

        return {
            'abcd': 'abc'
        }

    def get_public_key(self, request, repo_slug):
        """/repo/{slug} endpoint."""

        server = self.verify_token(request)

        self.logger.info("get_repo called with %s on server:%s", repo_slug, server)

        if server == "com":
            repo = self.com_projects.get(repo_slug)
        else:
            repo = self.org_projects.get(repo_slug)

        if repo is None:
            raise ErrorCode(404)

        if server == "com":
            key = self.com_key
        else:
            key = self.org_key

        public_key = key.publickey().export_key()

        return {
            'description': 'An RSA key',
            'public_key': public_key.decode('utf-8'),
            'fingerprint': 'abcd'
        }

    @classmethod
    def verify_token(cls, request):
        """Make sure we have the right token for access.

        Returns:
            str: "org" if we are on travis.org, "com" for travis.com
        """

        auth = request.headers.get('Authorization', None)
        if auth is None or (auth != 'token ORG_TOKEN' and auth != 'token COM_TOKEN'):
            raise ErrorCode(401)

        if auth == "token ORG_TOKEN":
            return "org"

        return "com"

    def quick_add_project(self, name, server="com"):
        proj = {

        }

        if server not in ("com", "org"):
            raise ValueError("Invalid server name: %s" % server)

        if server == "com":
            self.com_projects[name] = proj
        else:
            self.org_projects[name] = proj

    def _add_api(self, regex, callback):
        """Add an API matching a regex."""

        matcher = re.compile(regex)
        self.apis.append((matcher, callback))


    @classmethod
    def _parse_json(cls, request, *keys):
        data = request.get_data()
        string_data = data.decode('utf-8')

        try:
            injson = json.loads(string_data)

            if len(keys) == 0:
                return injson

            result = []

            for key in keys:
                if key not in injson:
                    raise ErrorCode(400)

                result.append(injson[key])

            return result
        except:
            raise ErrorCode(400)

    def __call__(self, environ, start_response):
        """Actual callback invoked for urls."""

        req = Request(environ)
        path = environ['PATH_INFO']

        self.request_count += 1

        for matcher, callback in self.apis:
            res = matcher.match(path)
            if res is None:
                continue

            groups = res.groups()

            try:
                data = callback(req, *groups)
                if data is None:
                    data = {}

                if isinstance(data, EncodedResponse):
                    response_headers = [(b'Content-type', data.encoding)]
                    resp = data.data
                else:
                    response_headers = [(b'Content-type', b'application/json')]
                    resp = json.dumps(data)
                    resp = resp.encode('utf-8')

                resp = Response(resp, status=200, headers=response_headers)
                return resp(environ, start_response)
            except JSONErrorCode as err:
                self.error_count += 1

                data = err.data
                if data is None:
                    data = {}

                resp = json.dumps(data)
                response_headers = [(b'Content-type', b'application/json')]
                resp = Response(resp.encode('utf-8'), status=err.status, headers=response_headers)
                return resp(environ, start_response)
            except ErrorCode as err:
                self.error_count += 1

                response_headers = [(b'Content-type', b'text/plain')]
                resp = Response(b"Error serving request\n", status=err.status, headers=response_headers)
                return resp(environ, start_response)

        self.error_count += 1

        response_headers = [(b'Content-type', b'text/plain')]
        resp = Response(b"Page not found.", status=404, headers=response_headers)
        return resp(environ, start_response)


@pytest.fixture(scope="session")
def travis_base():
    """A Mock travis instance."""

    travis = MockTravisCI()

    # Generate a new fake, unverified ssl cert for this server
    server = WSGIServer(application=travis)

    server.start()
    url = server.url

    yield travis, url

    server.stop()


@pytest.fixture
def travis(travis_base, monkeypatch):
    travis, url = travis_base

    monkeypatch.setenv('TRAVIS_ORG_URL', url)
    monkeypatch.setenv('TRAVIS_TOKEN_ORG', 'ORG_TOKEN')
    monkeypatch.setenv('TRAVIS_COM_URL', url)
    monkeypatch.setenv('TRAVIS_TOKEN_COM', 'COM_TOKEN')

    travis.reset()
    yield travis
    travis.reset()


@pytest.fixture
def travis_url(travis_base, monkeypatch):
    _travis, url = travis_base

    monkeypatch.setenv('TRAVIS_ORG_URL', url)
    monkeypatch.setenv('TRAVIS_TOKEN_ORG', 'ORG_TOKEN')
    monkeypatch.setenv('TRAVIS_COM_URL', url)
    monkeypatch.setenv('TRAVIS_TOKEN_COM', 'COM_TOKEN')

    return url
