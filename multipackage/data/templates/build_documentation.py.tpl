"""Single script that autobuilds all documentation."""

import sys
import shutil
import os
import time
import subprocess
import platform

from generate_api import main as api_main
from components import COMPONENTS

TOPLEVEL_PACKAGES = {
{% for key, packages in toplevel_packages |dictsort %}
    "{{ key }}": [{{ packages | map('quote') | join(", ") }}]{% if not loop.last %},{% endif %}

{% endfor %}
}

DESIRED_PACKAGES = {
{% for key, packages in desired_packages |dictsort %}
    "{{ key }}": [{{ packages | map('quote') | join(", ") }}]{% if not loop.last %},{% endif %}

{% endfor %}
}

{% if namespace %}
NAMESPACE = "{{ namespace }}"
{% else %}
NAMESPACE = None
{% endif %}


def delete_with_retry(folder):
    """Try multiple times to delete a folder.

    This is required on windows because of things like:
    https://bugs.python.org/issue15496
    https://blogs.msdn.microsoft.com/oldnewthing/20120907-00/?p=6663/
    https://mail.python.org/pipermail/python-dev/2013-September/128350.html
    """

    folder = os.path.abspath(os.path.normpath(folder))

    for _i in range(0, 5):
        try:
            if os.path.exists(folder):
                shutil.rmtree(folder)

            return
        except Exception:
            time.sleep(0.1)

    print("Could not delete directory after 5 attempts: %s" % folder)
    sys.exit(1)


def copy_with_retry(src, dst):
    """Try multiple times to delete a folder.

    This is required on windows because of things like:
    https://bugs.python.org/issue15496
    https://blogs.msdn.microsoft.com/oldnewthing/20120907-00/?p=6663/
    https://mail.python.org/pipermail/python-dev/2013-September/128350.html
    """

    src = os.path.abspath(os.path.normpath(src))
    dst = os.path.abspath(os.path.normpath(dst))

    for _i in range(0, 5):
        try:
            if os.path.exists(dst):
                delete_with_retry(dst)

            shutil.copytree(src, dst)
            return
        except:
            time.sleep(0.1)

    print("Could not copy directory after 5 attempts")
    sys.exit(1)


def get_package_folders():
    """Get all package folders that we should generate api docs for."""

    folders = []
    for key, component in COMPONENTS.items():
        packages = TOPLEVEL_PACKAGES[key]

        for package in packages:
            path = os.path.join(component['path'], package)
            folders.append(path)

    return folders


def copy_release_notes(base_folder, out_folder):
    """Copy all release notes into documentation folder."""

    dest_folder = os.path.join(out_folder, "release_notes")
    if not os.path.exists(dest_folder):
        os.mkdir(dest_folder)

    for key, component in COMPONENTS.items():
        src_path = os.path.join(base_folder, component['path'], 'RELEASE.md')
        dst_path = os.path.join(dest_folder, key + ".md")

        if not os.path.exists(src_path):
            print("Not copying release notes for %s because RELEASE.md does not exist." % key)
            continue

        print("Copying release notes for %s from %s" % (key, src_path))
        shutil.copyfile(src_path, dst_path)


def generate_args(folders, extra_args=None):
    base_folder = os.path.join(os.path.dirname(__file__), '..', '..')
    template_folder = os.path.join(base_folder, "doc", "_template")

    outdir = os.path.join(base_folder, ".tmp_docs", "api")

    args = ['-o', str(outdir), "-t", template_folder] + folders
    if extra_args is not None:
        args += extra_args

    return args


def main():
    base_folder = os.path.join(os.path.dirname(__file__), '..', '..')
    output_folder = os.path.join(base_folder, ".tmp_docs")
    dest_folder = os.path.join(base_folder, "built_docs")

    print("\n---- Copying docs to temporary folder ----\n")
    delete_with_retry(output_folder)
    copy_with_retry(os.path.join(base_folder, "doc"), output_folder)

    folders = get_package_folders()
    
    extra_args=['-r', 'modules.rst']
    if NAMESPACE is not None:
        extra_args.extend(['-r', "%s.rst" % NAMESPACE])

    args = generate_args(folders, extra_args=extra_args)

    print("\n---- Generating API docs ----\n")

    print("generate_api.py " + " ".join(args) + '\n')

    api_main(args)

    # sphinx-build on windows powershell leaves the terminal in a weird state
    # so disable color on windows
    args = ["sphinx-build", "-W", "-E", "-b", "html", output_folder, dest_folder]
    if platform.system() == 'Windows':
        args.insert(1, "--no-color")

    print("\n---- Copying release notes ----\n")
    copy_release_notes(base_folder, output_folder)

    print("\n---- Cleaning any old docs ----\n")
    delete_with_retry(dest_folder)

    print("\n---- Running Sphinx to generate docs ----\n")
    try:
        subprocess.check_output(args)
    except subprocess.CalledProcessError as err:
        return err.returncode

    print("\nAdding .nojekyll file")
    with open(os.path.join(dest_folder, ".nojekyll"), "w"):
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
