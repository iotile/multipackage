"""Tests to make sure api doc generation works cross platform."""

import os
from multipackage.data.scripts.generate_api import main as generate_main
from multipackage.utilities import directory_hash

def get_args(tmpdir, extra_args=None):
    base_folder = os.path.join(os.path.dirname(__file__), '..', 'multipackage')
    template_folder = os.path.join(base_folder, "data", "templates")

    outdir = tmpdir.mkdir("api")

    args = ['-o', str(outdir), "-t", template_folder, base_folder]
    if extra_args is not None:
        args += extra_args

    return args, str(outdir)


def test_stable_generation(tmpdir):
    """Make sure we can generate the same files on python 2/3."""

    args, outdir = get_args(tmpdir)

    generate_main(args)
    hash_value = directory_hash(outdir, "*.rst")

    # Make sure this output format stays constant, will need to
    # be updated as this package is updated.
    print("If this test fails, the multipackage api may have just changed")
    print("and you need to update the encoded hash in this test")
    print("Actual Hash: %s" % hash_value)
    assert hash_value == 'MD5:4D33651ED986501E606F28FF015B7141'