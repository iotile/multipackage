"""A simple mock slack webhook api."""

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


class MockSlack:
    """A test instance of the Travis-CI for continuous integration."""


    def __init__(self, ):
        if not HAS_DEPENDENCIES:
            raise RuntimeError("You must have pytest and pytest_localserver installed to be able to use MockIOTileCloud")

        self.logger = logging.getLogger(__name__)

        self.reset()

        self.apis = []
        self._add_api(r"/", self.post_hook)

    def reset(self):
        """Clear any stored data in in this cloud as if we created a new instance."""

        self.request_count = 0
        self.error_count = 0

    def post_hook(self, request):
        """/repo/{slug} endpoint."""

        return {
            'result': 'okay'
        }

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
def slack_base():
    """A Mock travis instance."""

    slack = MockSlack()

    # Generate a new fake, unverified ssl cert for this server
    server = WSGIServer(application=slack)

    server.start()
    url = server.url

    yield slack, url

    server.stop()


@pytest.fixture
def slack(slack_base, monkeypatch):
    slack, url = slack_base

    slack.reset()

    yield slack
    slack.reset()


@pytest.fixture
def slack_url(slack_base, monkeypatch):
    _slack, url = slack_base

    return url


if __name__ == '__main__':
    slack = MockSlack()
    import time
    # Generate a new fake, unverified ssl cert for this server
    server = WSGIServer(application=slack)

    server.start()
    try:

        url = server.url
        print("Server running at %s" % url)
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
