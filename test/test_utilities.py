"""Make sure our utilities work correctly."""

from builtins import open
import os
import platform
from multipackage.utilities import ManagedFileSection, dict_hash, find_toplevel_packages


def data_path(tmpdir, name, allow_empty=False):
    """Return the path to a copied data file."""

    base_dir = os.path.dirname(__file__)
    base_path = os.path.join(base_dir, "data", name)

    tmpfile = tmpdir.join(name)

    if not allow_empty and not os.path.exists(base_path):
        raise ValueError("Missing data file %s" % base_path)

    if os.path.exists(base_path):
        with open(base_path, "rb") as infile:
            data = infile.read()

        tmpfile.write_binary(data)

    return str(tmpfile)


def compare_files(comp, reference_name):
    """Binary file comparison."""

    base_dir = os.path.dirname(__file__)
    base_path = os.path.join(base_dir, "data", reference_name)

    with open(comp, "rb") as infile:
        act_data = infile.read()

    with open(base_path, "rb") as infile:
        ref_data = infile.read()

    assert act_data == ref_data


def test_no_section(tmpdir):
    """Make sure we can parse and update a file with no section."""

    path = data_path(tmpdir, "file_no_section.txt")

    section = ManagedFileSection(path)
    assert section.file_exists is True
    assert section.has_section is False
    assert section.modified is False
    assert section.other_lines == [".hello", ".git", "abcd", "asfd"]

    lines = ["test 1", "test 2", "test 3"]

    # Test native line ending detection
    if platform.system() == "Windows":
        assert section.line_ending == "\r\n"
    else:
        assert section.line_ending == "\n"

    section.update(lines)

    section2 = ManagedFileSection(path)
    assert section2.file_exists is True
    assert section2.has_section is True
    assert section2.modified is False

    assert section2.section_contents == ["test 1", "test 2", "test 3"]


def test_crlf_section(tmpdir):
    """Make sure we properly parse and recreate crlf files."""

    path = data_path(tmpdir, "file_with_section_crlf.nochange.txt")

    section = ManagedFileSection(path)
    assert section.file_exists is True
    assert section.has_section is True
    assert section.modified is False
    assert section.other_lines == ["abcd", "asf", "b"]

    section.update(section.section_contents)

    compare_files(path, "file_with_section_crlf.nochange.txt")


def test_lf_section(tmpdir):
    """Make sure we properly parse and recreate crlf files."""

    path = data_path(tmpdir, "file_with_section_lf.nochange.txt")

    section = ManagedFileSection(path)
    assert section.file_exists is True
    assert section.has_section is True
    assert section.modified is False
    assert section.other_lines == ["abcd", "asf", "b"]

    section.update(section.section_contents)

    compare_files(path, "file_with_section_lf.nochange.txt")


def test_start_end_delimiter(tmpdir):
    """Make sure we can parse files with an ending delimiter."""

    path = data_path(tmpdir, "file_start_end.txt")

    section = ManagedFileSection(path, delimiter_start="<!-- ", delimiter_end=" -->")
    assert section.file_exists is True
    assert section.has_section is True
    assert section.modified is False


def test_dict_hash():
    """Make sure we can repeatably hash dictionaries."""

    obj = {
        'test1': 15.0,
        'test2': 5,
        'test5': {
            "string_key": [1, 2, 3]
        }
    }

    hash_value = dict_hash(obj)
    assert hash_value == "MD5:07358855AB401EE3EAB3167DA585C70A"


def test_find_toplevel_packages():
    """Make sure we can find top level packages."""

    packages = find_toplevel_packages(os.path.join(os.path.dirname(__file__), '..'))
    assert packages == ['multipackage']
