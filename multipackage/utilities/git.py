"""Basic git operations."""

import subprocess
import os
import re
from ..exceptions import UsageError, MissingPackageError


class GITRepository:
    """Helper class for git repository functionality.

    Args:
        path (str): The path to a git repository folder.
    """

    def __init__(self, path):
        self.path = os.path.normpath(os.path.abspath(path))

        # Ensure git is installed and we point to a valid repository
        self.version()
        self.status()

    def status(self):
        """Call git status and parse the results."""

        try:
            contents = subprocess.check_output(['git', '-C', self.path, 'status', '--porcelain=v2', '-b'], stderr=subprocess.PIPE)
            contents = contents.decode('utf-8')
        except subprocess.CalledProcessError:
            raise UsageError("Not a valid git repository: %s" % self.path, "Make sure the path is correct")

        return contents.split()

    def remote(self, name="origin"):
        """Get the remote origin URL.

        Args:
            name (str): The name of the remote to get.

        Returns:
            str: The remote URL.
        """

        contents = subprocess.check_output(['git', '-C', self.path, 'remote', 'get-url', name])
        contents = contents.decode('utf-8')
        return contents.rstrip()

    def github_name(self, name="origin"):
        """Get the user/org and repo name for a github hosted repo.

        Args:
            name (str): The name of the remote to get.

        Returns:
            (str, str): The github org/username and repo name.
        """

        remote = self.remote(name)
        info = extract_github_name(remote)
        if info is None:
            raise UsageError("Git repository could not be parsed: %s" % remote, "Make sure the repository is hosted on github")

        return info

    @classmethod
    def version(cls):
        """Return the version of git installed."""

        try:
            version_string = subprocess.check_output(['git', '--version'])
            version_string = version_string.decode('utf-8')
        except subprocess.CalledProcessError:
            raise MissingPackageError("git", "Git must be installed")

        return version_string.rstrip()



_SSH_REGEX = r"git@github\.com:(?P<user>[a-zA-Z0-9_\-]+)/(?P<repo>[a-zA-Z0-9_\-]+)\.git"
_HTTPS_REGEX = r"https://github\.com/(?P<user>[a-zA-Z0-9_\-]+)/(?P<repo>[a-zA-Z0-9_\-]+)\.git"

def extract_github_name(remote):
    """Extract a github name from a remote URL.

    Args:
        remote (str): A git remote URL

    Returns:
        (str, str): The user and repo names.

        If the repo cannot be found or is not hosted on Github, None is
        Returned.
    """

    result = re.match(_SSH_REGEX, remote)
    if result is not None:
        return result.group('user'), result.group('repo')

    result = re.match(_HTTPS_REGEX, remote)
    if result is not None:
        return result.group('user'), result.group('repo')

    return None
