"""Tests of ManifestFile class."""

import pytest


def test_basic_behavior(init_repo):
    """Make sure everything works in the default case."""

    init_repo.manifest.verify_all(report=True)
    assert len(init_repo.errors) == 0
    assert len(init_repo.warnings) == 0

    assert init_repo.initialized
    assert not init_repo.settings_changed
