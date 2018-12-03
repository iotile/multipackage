"""Unit tests of the Repository class."""

import pytest
from multipackage.exceptions import InternalError, InvalidSettingError, InvalidEnvironmentError


def test_env_variables(init_repo, monkeypatch):
    """Make sure we can set and get environment variables."""

    init_repo.required_secret('HELLO', 'sub1', 'greeting', context="build")
    init_repo.optional_secret('GOODBYE', 'sub2', 'goodbye')
    init_repo.optional_secret('HELLO', 'sub2', 'other usage', context="deploy")

    with pytest.raises(InternalError):
        init_repo.get_secret('HELLO2')

    with monkeypatch.context() as monkey:
        monkey.delenv('HELLO', raising=False)
        monkey.delenv('GOODBYE', raising=False)

        with pytest.raises(InvalidEnvironmentError):
            init_repo.get_secret('HELLO')

        assert init_repo.get_secret('GOODBYE') is None


def test_settings(init_repo):
    """Make sure we can get and set settings."""

    assert init_repo.get_setting('doc.deploy', default='a') == 'a'

    with pytest.raises(InvalidSettingError):
        init_repo.get_setting('doc.deploy')

    assert 'doc' not in init_repo.options

    init_repo.set_setting('doc.deploy', 'abc')
    assert init_repo.get_setting('doc.deploy') == 'abc'

    assert 'doc' in init_repo.options
    assert init_repo.options['doc'] == {
        'deploy': 'abc'
    }

    # Make sure we don't overwrite keys with dicts
    with pytest.raises(InvalidSettingError) as error:
        init_repo.set_setting('doc.deploy.test', 'abc')

    assert error.value.variable_name == "doc.deploy.test"
