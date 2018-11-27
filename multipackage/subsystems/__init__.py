"""Supported subsystems that manage different aspects of the repository."""

from .linting import LintingSubsystem
from .basic import BasicSubsystem
from .travis import TravisSubsystem

__all__ = ['LintingSubsystem', 'BasicSubsystem', 'TravisSubsystem']
