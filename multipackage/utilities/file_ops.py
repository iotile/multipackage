"""Helper utilities for file operations."""

from builtins import open
import platform
import os
import json


def atomic_save(target_path, data, encoding="utf-8"):
    """Attempt to atomically save file by saving and then moving into position

    The goal is to make it difficult for a crash to corrupt our data file
    since the move operation can be made atomic if needed on mission critical
    filesystems.  This operation uses os.rename on non-Windows systems for
    atomic updates but normal saves on Windows since atomic semantics are not
    properly supported.

    Args:
        target_path (str): The final path that the file should have.
        data (str): The data that we want to save.
        encoding (str): The file encoding that we should use, defaults
            to utf-8 if not specified.
    """

    if platform.system() == 'Windows':
        with open(target_path, "w", encoding=encoding, newline='') as outfile:
            outfile.write(data)

        return

    real_path = os.path.realpath(target_path)
    new_path = real_path + '.new'

    with open(new_path, "w", encoding=encoding, newline='') as outfile:
        outfile.write(data)

    os.rename(new_path, real_path)


def atomic_json(target_path, obj):
    """Atomically dump a dict as a json file.

    Args:
        target_path (str): The final path that the file should have.
        obj (dict): The dictionary that should be dumped.
    """

    data = json.dumps(obj, indent=4)

    if isinstance(data, bytes):
        data = data.decode('utf-8')

    atomic_save(target_path, data)
