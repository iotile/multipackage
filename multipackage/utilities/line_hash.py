"""Calculate a hex checksum over a list of lines."""

from __future__ import unicode_literals
import hashlib


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

    md5 = hashlib.md5()
    md5.update(data)

    return "MD5:" + md5.hexdigest().upper()
