"""Shared test fixtures."""

import pytest
from multipackage import Repository

pytest_plugins = ['mock_travis', 'mock_pypi', 'mock_slack']


@pytest.fixture(scope="function")
def bare_repo(tmpdir):
    """Return a repository pointed at a bare repo."""

    folder = str(tmpdir.mkdir("bare_repo"))

    return Repository(folder)


@pytest.fixture(scope="function")
def init_repo(tmpdir, monkeypatch):
    """Return a repository pointed at an iniitialized repo (without update called)."""

    folder = str(tmpdir.mkdir("init_repo"))

    monkeypatch.setenv('GITHUB_TOKEN', "github_token")
    monkeypatch.setenv('PYPI_USER', 'test_user')
    monkeypatch.setenv('PYPI_PASS', 'test_pass')
    monkeypatch.setenv('SLACK_TOKEN', 'test_slack_token')
    monkeypatch.setenv('SLACK_WEB_HOOK', 'http://127.0.0.1:8000/nothing')

    repo = Repository(folder)
    repo.initialize()

    return Repository(folder)
