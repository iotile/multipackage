"""Supported subsystems that manage different aspects of the repository."""

from .linting import LintingSubsystem
from .basic import BasicSubsystem
from .travis import TravisSubsystem
from .docs import DocumentationSubsystem

__all__ = ['LintingSubsystem', 'BasicSubsystem', 'TravisSubsystem', 'DocumentationSubsystem']
