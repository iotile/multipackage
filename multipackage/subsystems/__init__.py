"""Supported subsystems that manage different aspects of the repository."""

from .pylint import PylintLinter
from .basic import BasicPythonSupport
from .travis import TravisSubsystem
from .sphinx import SphinxDocumentation

__all__ = ['PylintLinter', 'BasicPythonSupport', 'TravisSubsystem', 'SphinxDocumentation']
