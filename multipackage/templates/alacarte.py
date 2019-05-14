"""Basic Repo Template that reads subsystem definitions from a config file.

This template allows the user to choose exactly what subsystems to install and
manage them manually.
"""

import logging
from ..exceptions import InvalidSettingError
from .repo_template import RepositoryTemplate
from ..subsystems import SphinxDocumentation
from ..subsystems import BasicPythonSupport


class ManualTemplate(RepositoryTemplate):
    SHORT_NAME = "manual"
    SHORT_DESCRIPTION = "Manually installs subsystems"
    INFO_TEMPLATE = "manual_info_template.tpl"
    DOCTOR_TEMPLATE = "manual_doctor_template.tpl"

    def __init__(self):
        super(ManualTemplate, self).__init__()

        self._logger = logging.getLogger(__name__)

    def install(self, repo):
        """Install this template into a Repository object.

        See :meth:`RepositoryTemplate.install`

        Args:
            repo (Repository): The repository where we should install this template.
        """

        for subsystem in repo.options.get('subsystems', []):
            name = subsystem.get('name')
            args = subsystem.get('args', {})

            if name is None:
                raise InvalidSettingError('subsystem name', 'missing in settings file.')

            if name != 'SphinxDocumentation':
                raise InvalidSettingError('subsystem name', "name '{}' is unknown".format(name))

            repo.add_subsystem(SphinxDocumentation(repo, **args))

        repo.add_subsystem(BasicPythonSupport(repo))
