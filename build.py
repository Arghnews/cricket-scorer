#!/usr/bin/env python3

import os
import platform
import re
import shlex
import operator
import subprocess
import sys

from packaging import version


def make_app_name(app_name):
    system = platform.system()  # Windows, Ubuntu, etc.
    name = [app_name]

    if system == "Windows":
        win_ver = platform.win32_ver()[0]  # "10"
        name.append(system + win_ver)
    else:
        name.append(system)

    bits_str = platform.architecture()[0]  # "32bits", "64bits"
    name.append(bits_str)

    if system == "Windows":
        name.append("exe")

    return ".".join(name)


def find_upx():
    """Find a folder like upx-3.96-win64 in the current dir, return the path to
    it else return None

    Currently only implemented for windows
    """

    # https://stackoverflow.com/a/59938961/8594193
    list_subfolders_with_paths = [f.path for f in os.scandir(".") if f.is_dir()]

    # As per https://packaging.pypa.io/en/latest/version.html
    upx_folder_reg = re.compile(r".\\upx-(" + version.VERSION_PATTERN + r")-win64",
                                re.VERBOSE | re.IGNORECASE)

    version_to_path = {}
    for d in list_subfolders_with_paths:
        m = re.match(upx_folder_reg, d)
        if m:
            version_to_path[version.parse(m.group(1))] = d

    if not version_to_path:
        return None
    return max(version_to_path.items(), key=operator.itemgetter(1))[1]


def main():

    app_name = make_app_name("cricket_scorer")
    package_base = os.path.normpath("src/cricket_scorer")
    data_prefix = os.path.join(package_base, "data", "icons")
    executable = os.path.normpath("./template_gui.py")
    icon_path = os.path.join(data_prefix, "cricket.ico")

    upx_path, upx = find_upx(), ""
    assert upx_path is not None
    if upx_path is not None:
        upx = "--upx-dir=" + os.path.normpath(upx_path)

    cmd = f"""pyinstaller.exe
        --noconfirm
        -p "{package_base}"
        --collect-data "cricket_scorer.data"
        --icon "{icon_path}"
        --hidden-import plyer.platforms.win.notification
        --add-data "LICENSE.txt{os.pathsep}."
        --add-data "COPYING.LESSER{os.pathsep}."
        --add-data "license_header.txt{os.pathsep}."
        {upx}
        -n {app_name}
        --clean
        --onefile
        --windowed
        {executable}
    """

    cmd = re.sub(r"\s+", " ", cmd)
    cmd = shlex.split(cmd)
    print("Running:", cmd)
    subprocess.run(cmd)


if __name__ == "__main__":
    sys.exit(main())
