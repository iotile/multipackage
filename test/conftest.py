"""Shared test fixtures."""

import pytest
from multipackage import Repository


@pytest.fixture(scope="function")
def bare_repo(tmpdir):
    """Return a repository pointed at a bare repo."""

    folder = str(tmpdir.mkdir("bare_repo"))

    return Repository(folder, nogit=True)


@pytest.fixture(scope="function")
def init_repo(tmpdir):
    """Return a repository pointed at an iniitialized repo (without update called)."""

    folder = str(tmpdir.mkdir("init_repo"))

    repo = Repository(folder, nogit=True)
    repo.initialize()

    return Repository(folder, nogit=True)
