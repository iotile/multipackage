"""Integration tests of the whole multipackage process."""

import os
import subprocess
import shutil
import pytest
from multipackage.scripts.multipackage import main as multipackage_main


def copy_repo(name, dest_folder, init_git=True, git_remote="git@github.com:com/my_package.git"):
    """Copy a repository to dest_folder."""

    base_dir = os.path.join(os.path.dirname(__file__), 'repos')
    source_dir = os.path.join(base_dir, name)

    shutil.copytree(source_dir, dest_folder)

    if not init_git:
        return

    curr_dir = os.getcwd()

    try:
        os.chdir(dest_folder)
        subprocess.check_call(['git', 'init'])
        subprocess.check_call(['git', 'remote', 'add', 'origin', git_remote])
    finally:
        os.chdir(curr_dir)


def run_in_sandbox(args, pypi_url=None, slack=None):
    """Run a command with env variables to point to local servers and proper pythonpath.

    This sandbox is designed to protect us from accessing any actual third
    party services. In particular it makes sure that no pypi credentials that
    could be used to actually release a package make into the environment.
    Similarly, it makes sure that slack notifications are turned off unless a
    local test server is setup.
    """

    env = os.environ.copy()

    env['PYTHONPATH'] = os.path.abspath(os.getcwd())
    print("Running in %s" % os.getcwd())

    if slack is not None:
        env['SLACK_WEB_HOOK'] = slack
    elif 'SLACK_WEB_HOOK' in env:
        del env['SLACK_WEB_HOOK']

    env['PYPI_USER'] = 'test_user'
    env['PYPI_PASS'] = 'test_pass'

    if pypi_url is not None:
        env['PYPI_URL'] = pypi_url
    elif 'PYPI_URL' in env:
        del env['PYPI_URL']

    proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = proc.communicate()
    code = proc.returncode

    if not isinstance(stdout, str):
        stdout = stdout.decode('utf-8')

    if not isinstance(stderr, str):
        stderr = stderr.decode('utf-8')

    print('--------- Call to %s ---------' % ' '.join(args))
    print(stdout)
    print('--------- stderr     ---------')
    print(stderr)

    return code, stdout, stderr


@pytest.fixture(scope='function')
def bare_repo(tmpdir, travis, monkeypatch):
    """Copy a bare repo into a temporary directory."""

    folder = str(tmpdir.join('repo2'))
    copy_repo('test_project', folder)

    curr_dir = os.getcwd()
    try:
        os.chdir(folder)
        monkeypatch.syspath_prepend(os.path.abspath(folder))
        monkeypatch.setenv('GITHUB_TOKEN', "github_token")
        monkeypatch.setenv('PYPI_USER', 'test_user')
        monkeypatch.setenv('PYPI_PASS', 'test_pass')

        yield folder
    finally:
        os.chdir(curr_dir)


@pytest.fixture(scope='function')
def py2_repo(bare_repo):
    """Create an updated python 2 repository."""

    multipackage_main(['init'])

    with open(os.path.join("scripts", "components.txt"), 'a') as outfile:
        outfile.write('\nmy_package: ./, compatibility=python2\n')

    multipackage_main(['update'])

    return bare_repo


@pytest.fixture(scope='function')
def py3_repo(bare_repo):
    """Create an updated python 2 repository."""

    multipackage_main(['init'])

    with open(os.path.join("scripts", "components.txt"), 'a') as outfile:
        outfile.write('\nmy_package: ./, compatibility=python3\n')

    multipackage_main(['update'])
    return bare_repo


@pytest.fixture(scope='function')
def uni_repo(bare_repo):
    """Create an updated python 2 repository."""

    multipackage_main(['init'])

    with open(os.path.join("scripts", "components.txt"), 'a') as outfile:
        outfile.write('\nmy_package: ./, compatibility=universal\n')

    multipackage_main(['update'])

    return bare_repo


def test_unitialized_info(bare_repo, capsys):
    """Test multipackage init."""

    multipackage_main(['info'])


def test_update(bare_repo):
    """Make sure multipackage update works."""

    multipackage_main(['init'])

    with open(os.path.join("scripts", "components.txt"), 'a') as outfile:
        outfile.write('\nmy_package: ./, compatibility=python2\n')

    multipackage_main(['-vvvvv', 'update'])


def test_build_docs(uni_repo, capsys):
    """Make sure we can build documentation."""

    run_in_sandbox(['python', os.path.join('scripts', 'build_documentation.py')])


def test_twine_testrelease(uni_repo, pypi_url, slack, slack_url):
    """Make sure we can test a release without actually releasing."""

    retval, _stdout, _stderr = run_in_sandbox(['python', os.path.join('scripts', 'release_by_name.py'), 'test@my_package-0.0.1'],
                                              pypi_url=pypi_url)
    assert retval == 0
    assert slack.request_count == 0
    assert slack.error_count == 0


    retval, _stdout, _stderr = run_in_sandbox(['python', os.path.join('scripts', 'release_by_name.py'), 'test@my_package-0.0.1'],
                                              pypi_url=pypi_url, slack=slack_url)
    assert retval == 0
    assert slack.request_count == 1
    assert slack.error_count == 0


def test_twin_release(uni_repo, pypi_url, pypi, slack, slack_url):
    """Make sure we can release for real."""

    retval, _stdout, _stderr = run_in_sandbox(['python', os.path.join('scripts', 'release_by_name.py'), 'my_package-0.0.1'],
                                              pypi_url=pypi_url)
    assert retval == 0
    assert pypi.request_count == 2
    assert pypi.error_count == 0

    retval, _stdout, _stderr = run_in_sandbox(['python', os.path.join('scripts', 'release_by_name.py'), 'my_package-0.0.1'],
                                              pypi_url=pypi_url, slack=slack_url)
    assert retval == 0
    assert pypi.request_count == 4
    assert pypi.error_count == 0
    assert slack.request_count == 1
    assert slack.error_count == 0
