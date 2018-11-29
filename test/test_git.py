"""Tests of the GITRepository class."""

import os
import pytest
from multipackage.utilities import GITRepository
from multipackage.utilities.git import extract_github_name
from multipackage.exceptions import UsageError


REPO_DIR = os.path.join(os.path.dirname(__file__), '..')
NONREPO_DIR = os.path.join(REPO_DIR, '..')

def test_git_remote():
    """Ensure that git remote works.

    Note that we check both clone URLS since travis uses https to clone rather
    than ssh."""

    repo = GITRepository(REPO_DIR)
    assert repo.remote() in ("git@github.com:iotile/multipackage.git",
                             "https://github.com/iotile/multipackage.git")

    with pytest.raises(UsageError):
        GITRepository(NONREPO_DIR)


def test_git_matching():
    """Make sure we can extract github identifiers from a URL."""

    repo = GITRepository(REPO_DIR)

    org, repname = repo.github_name()
    assert org == "iotile"
    assert repname == "multipackage"

    assert extract_github_name("git@github.com:user1/Test_-3.git") == ('user1', 'Test_-3')
    assert extract_github_name("https://github.com/iotile/python_multipackage.git") == ('iotile', 'python_multipackage')
    assert extract_github_name("https://gitlab.com/patrologia/mega.git") is None
