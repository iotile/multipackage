"""Calculate a hex checksum over a list of lines."""

from __future__ import unicode_literals
import hashlib
import json
import fnmatch
import os


def line_hash(lines, method="md5"):
    r"""Calculate a hash over a list of strings.

    The strings are all joined with '\n' characters to canonicalize them so
    that line endings are not part of the calculated hash.

    Args:
        lines (list of str): The list of strings to hash
        method (str): The name of the hash method, currently
            only md5 is supported.

    Returns:
        str: The hash digest as a hex string in uppercase.
    """

    if method != 'md5':
        raise ValueError("Unsupported hash algorithm: %s" % method)


    data = "\n".join([x.rstrip('\r\n') for x in lines])
    return _md5_hash(data)


def dict_hash(obj, method="md5"):
    r"""Calculate a hash over a json-serializable dictionary.

    The obj argument will be dumped to a json string with sorted
    keys encoded as utf-8 and then that string will be hashed to
    produce the hash value.

    Args:
        obj (dict): The json serializable dictionary that should
            be hashed.
        method (str): The name of the hash method, currently
            only md5 is supported.

    Returns:
        str: The hash digest as a hex string in uppercase.
    """

    if method != 'md5':
        raise ValueError("Unsupported hash algorithm: %s" % method)

    data = json.dumps(obj, sort_keys=True)
    return _md5_hash(data)



def directory_hash(path, glob="*"):
    """Hash all files in a given folder.

    This will return a hash value that will tell you if any file has changed
    in the given directory.  You can calculate the hash only over a specific
    subset of the files by using glob which will be passed to fnmatch to
    select files.

    The hash value will detect:
     - a file is added
     - a file is removed
     - a file name is changed
     - a file is changed in anyway

    The hash value is stable on multiple operating systems and across line
    endings for text files.  The name of the parent directory is not part of
    the hash value so it is useful for ensuring that a given folder has the
    same contents.

    **This function assumes all files are text files and calculates a
    line-ending independing hash**

    Args:
        path (str): The path to the directory that we want to hash.
        glob (str): Optional wildcard specifier for selecting which
            files should be hashed.

    Returns:
        str: The hash digest as a hex string in uppercase.
    """

    files = os.listdir(path)
    selected = fnmatch.filter(files, glob)
    selected.sort()

    md5 = hashlib.md5()
    hashes = [line_hash(x) for x in selected]

    md5.update(b"START OF DIRECTORY")
    md5.update(b"File count: %d" % len(selected))

    for name, hash_value in zip(selected, hashes):
        md5.update(b"START OF FILE: " + name.encode('utf-8'))
        md5.update(hash_value.encode('utf-8'))

    md5.update(b"END OF DIRECTORY")
    return "MD5:" + md5.hexdigest().upper()


def _md5_hash(data):
    if not isinstance(data, bytes):
        data = data.encode('utf-8')

    md5 = hashlib.md5()
    md5.update(data)

    return "MD5:" + md5.hexdigest().upper()
