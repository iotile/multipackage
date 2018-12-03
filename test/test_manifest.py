"""Tests of ManifestFile class."""


def test_basic_behavior(init_repo):
    """Make sure everything works in the default case."""

    init_repo.manifest.verify_all(report=True)
    assert init_repo.count_messages('error') == 0
    assert init_repo.count_messages('warning') == 0

    assert init_repo.initialized
    assert not init_repo.settings_changed
