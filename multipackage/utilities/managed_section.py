"""Helper class for managing a block of content inside a text file."""

from __future__ import unicode_literals
import os
import platform
from builtins import open
from .obj_hash import line_hash
from .file_ops import atomic_save
from ..exceptions import ManualInterventionError


class ManagedFileSection:
    """A section of a text file that is managed by multipackage.

    This class helps define a block of lines inside a file with
    a fence around them.  The contents of the fence are hashed
    so that modifications can be detected and the fence data
    can be versioned.

    Args:
        path (str): The path to the file that we want to manage.
            This file does not need to exist and will be created
            when you try to update it with data if it does not
            currently exist.
        delimiter_start (str): The character string that starts a managed file
            section block header line.  This is usually a comment character
            like '#'.
        delimiter_end (str): Optional charcter string that ends a managed file
            section block header line.  This defaults to an emptry string but
            can be set to a value if comments need to be explicitly closed
            such as delimiter_start="<!-- ", delimiter_end=" -->".
    """

    SECTION_START = "BEGIN MULTIPACKAGE MANAGED SECTION, HASH="
    SECTION_END = "END MULTIPACKAGE MANAGED SECTION"
    HASH_HEX_LENGTH = 32

    MANAGE_ERROR = "A file that needs to be managed by multipackage exists and is a directory, not a file"
    MULTIPLE_SECTION_ERROR = "A file that is managed by multipackage has been corrupted"

    def __init__(self, path, delimiter_start='# ', delimiter_end=''):
        self.path = path
        self._delimiter_start = delimiter_start
        self._delimiter_end = delimiter_end
        self.line_ending = self._native_line_ending()

        if os.path.isdir(self.path):
            raise ManualInterventionError(self.MANAGE_ERROR, self.path)

        self.file_exists = False
        self.has_section = False
        self.actual_hash = None
        self.section_contents = None
        self.other_lines = []
        self.modified = False
        self._start_line = 0

        if os.path.exists(self.path):
            self.file_exists = True
            self._load_section()

    @classmethod
    def _native_line_ending(cls):
        if platform.system() == "Windows":
            return "\r\n"

        return "\n"

    def _infer_line_ending(self, lines):
        found_counts = {
            '\n': 0,
            '\r\n': 0
        }

        for line in lines:
            if len(line) == 0:
                continue

            final_char = line[-1]
            if final_char == '\n' and len(line) >= 2 and line[-2] == '\r':
                final_char = '\r\n'

            if final_char not in found_counts:
                continue

            found_counts[final_char] = found_counts[final_char] + 1

        if found_counts['\n'] == 0 and found_counts['\r\n'] == 0:
            return self._native_line_ending()

        if found_counts['\r\n'] > found_counts['\n']:
            return '\r\n'

        return '\n'

    def _load_section(self):
        """Attempt to load a managed file section."""

        with open(self.path, "r", encoding="utf-8", newline='') as infile:
            lines = infile.readlines()

        self.line_ending = self._infer_line_ending(lines)

        start_line = None
        section_hash = None
        end_line = None
        for i, line in enumerate(lines):
            if not line.startswith(self._delimiter_start):
                continue

            line = line.rstrip('\r\n')
            line = line[len(self._delimiter_start):]
            if len(self._delimiter_end) > 0 and not line.endswith(self._delimiter_end):
                continue
            elif len(self._delimiter_end) > 0:
                line = line[:-len(self._delimiter_end)]

            if line.startswith(self.SECTION_START):
                if start_line is not None:
                    raise ManualInterventionError(self.MULTIPLE_SECTION_ERROR, self.path)

                start_line = i
                section_hash = line[len(self.SECTION_START):]
            elif line.startswith(self.SECTION_END):
                if start_line is None:
                    raise ManualInterventionError(self.MULTIPLE_SECTION_ERROR, self.path)

                end_line = i

        if start_line is None and end_line is None:
            self.other_lines = [x.rstrip('\r\n') for x in lines]
            return

        # Verify the section hash
        section_lines = [x.rstrip('\r\n') for x in lines[start_line + 1:end_line]]
        other_lines = lines[:start_line] + lines[end_line + 1:]
        other_lines = [x.rstrip('\r\n') for x in other_lines]

        actual_hash = line_hash(section_lines)

        self.has_section = True
        self.section_contents = section_lines
        self.other_lines = other_lines
        self.actual_hash = actual_hash
        self.modified = actual_hash != section_hash
        self._start_line = start_line

    def ensure_lines(self, lines, present=True):
        """Ensure that the given lines are present or absent in this file.

        Each line is added independently and no order is assumed. This method
        is idempotent so that you can call it repeatedly and each line will
        only be added once.  The lines must match exactly.

        The lines must be distinct.  If there are multiple copies of the same
        line in ``lines``, only one copy will be added to the file.

        Args:
            lines (list of str): A list of lines to add to the
                file if they are not present or remove from the file if they are.
                Whether the lines are added or removed is controlled by the
                ``present`` parameter.
            present (bool): If True, ensure lines are present (the default), if
                False, ensure lines are absent.
        """

        if present:
            if self.section_contents is None:
                self.section_contents = lines
            else:
                for line in lines:
                    if line not in self.section_contents:
                        self.section_contents.append(line)
        else:
            if self.section_contents is not None:
                self.section_contents = [x for x in self.section_contents if x not in lines]

        self.update()

    def update(self, lines=None):
        """Update or add a managed section into the file.

        This method will add a new managed section into the file or update the
        section that is currently there, replacing its contents with those
        specified in update.  The resulting file will we written out to disk.

        If the file does not currently exist, it will be created, otherwise
        its contents will be replaced.

        Args:
            lines (list of str): A list of lines to add to the
                file.  If this is passed as None, then the current value of
                self.section_contents will be used instead.
        """

        if lines is None:
            lines = self.section_contents

        if lines is None:
            lines = []

        hash_hex = line_hash(lines)

        start_line = self._delimiter_start + self.SECTION_START + hash_hex + self._delimiter_end
        end_line = self._delimiter_start + self.SECTION_END + self._delimiter_end

        new_section = [start_line] + lines + [end_line]

        lines = self.other_lines[:self._start_line] + new_section + self.other_lines[self._start_line:]

        # Always terminate with a final newline
        data = self.line_ending.join(lines) + self.line_ending
        atomic_save(self.path, data)

        self.section_contents = new_section
        self.has_section = True
        self.file_exists = True
