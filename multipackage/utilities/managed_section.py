"""Helper class for managing a block of content inside a text file."""

from __future__ import unicode_literals
import os
import re
import platform
from builtins import open
from .obj_hash import line_hash
from .file_ops import atomic_save
from ..exceptions import ManualInterventionError, InternalError


class ManagedFileSection(object):
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

    def ensure_lines(self, lines, match=None, present=True, multi=False):
        """Ensure that the given lines are present or absent in this file.

        Each line is added independently and no order is assumed. This method
        is idempotent so that you can call it repeatedly and each line will
        only be added once.  The lines must match exactly.

        The lines must be distinct.  If there are multiple copies of the same
        line in ``lines``, only one copy will be added to the file.

        If you need to perform fuzzy matching on a given line in order to
        properly update it, you can pass a list of regular expressions along
        with the lines

        Args:
            lines (list of str): A list of lines to add to the
                file if they are not present or remove from the file if they are.
                Whether the lines are added or removed is controlled by the
                ``present`` parameter.
            match (list of str): A list of regular expressions to
                use to match against a line.  If passed it must have the same
                length as lines and will be paired with each line in lines in
                order to determine which line matches.
            present (bool): If True, ensure lines are present (the default), if
                False, ensure lines are absent.
            multi (bool): If true, allow for matching and updating multiple lines
                for each line in ``lines``.  If False, InternalError is raised
                if there are multiple lines matching a given line.
        """

        if match is not None and len(match) != len(lines):
            raise InternalError("length of match expressions (len=%d) must match length of lines (len=%d)"
                                % (len(match), len(lines)))

        if present and self.section_contents is None:
            self.section_contents = lines
        elif not present and self.section_contents is None:
            pass
        else:
            for i, line in enumerate(lines):
                line_match = line
                if match is not None:
                    line_match = match[i]

                matches = self._find_line(line_match, self.section_contents, regex=match is not None)
                if len(matches) > 1 and not multi:
                    match_string = "\n".join(self.section_contents[i] for i in matches)
                    raise InternalError("Line %s in ManagedFileSection.ensure_lines matches multiple lines in file:\n%s"
                                        % (line_match, match_string))

                # If not in section add if present is True
                # If in section and present is True, update contents
                # If in section, remove if present is False
                if len(matches) == 0 and present:
                    self.section_contents.append(line)
                elif len(matches) != 0:
                    matches.sort(reverse=True)

                    if present:
                        for i in matches[:-1]:
                            del self.section_contents[i]

                        self.section_contents[matches[-1]] = line
                    else:
                        for i in matches:
                            del self.section_contents[i]

        self.update()

    @classmethod
    def _find_line(cls, match, lines, regex=False):
        if regex:
            compiled = re.compile(match)
            matcher = lambda x: compiled.match(x) is not None
        else:
            matcher = lambda x: x == match

        found = []

        for i, line in enumerate(lines):
            if matcher(line):
                found.append(i)

        return found

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

        new_contents = lines

        hash_hex = line_hash(lines)

        start_line = self._delimiter_start + self.SECTION_START + hash_hex + self._delimiter_end
        end_line = self._delimiter_start + self.SECTION_END + self._delimiter_end

        new_section = [start_line] + lines + [end_line]

        lines = self.other_lines[:self._start_line] + new_section + self.other_lines[self._start_line:]

        # Always terminate with a final newline
        data = self.line_ending.join(lines) + self.line_ending
        atomic_save(self.path, data)

        self.section_contents = new_contents
        self.has_section = True
        self.file_exists = True
