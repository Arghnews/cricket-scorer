import pathlib
import setuptools
import shutil

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# yapf: disable
install_requires = [
    "PySimpleGUI >= 4.45.0",
    "plyer >= 2.0.0",
    "packaging",
    "xlwings >= 0.24.1;platform_system=='Windows'",
    "smbus2;platform_system=='Linux'",
]

# package_data = {
#     "license": ["LICENSE.txt", "COPYING.LESSER",],
#     "icon": ["cricket.ico",],
## "third_party_licenses": [str(d) for d in pathlib.Path("licenses").rglob("*.txt")],
# }

# yapf: enable

# if platform.system() == "Windows":
#     install_requires += ["xlwings"]
# else:
#     install_requires += ["smbus2"]

# package_data = {"hello": ["licenses/plyer/LICENSE_INFO.txt"]}
# package_data = {"smackage": ["crap.txt"]}
package_data = {
    # If any package contains *.txt files, include them:
    # "": ["*.txt"],
    # And include any *.dat files found in the "data" subdirectory
    # of the "mypkg" package, also:
    "cricket_scorer": ["data/icons/cricket.ico", "data/licenses/*/*"],
}


def copy_licenses_to_data_dir():
    # Copy the LICENSE.txt (gplv3) and COPYING.LESSER (lgplv3) license files
    # from the project root into src/cricket_scorer/data/licenses/cricket_scorer
    # so they can be displayed in the GUI, and merge them into one file. Also
    # copy license_header.txt to the same folder and name it header.txt

    license_gplv3 = pathlib.Path("LICENSE.txt")
    license_lgplv3 = pathlib.Path("COPYING.LESSER")
    license_header = pathlib.Path("license_header.txt")
    assert license_gplv3.exists()
    assert license_lgplv3.exists()
    assert license_header.exists()

    root = pathlib.Path("src/cricket_scorer/data/licenses")
    assert root.exists() and root.is_dir()
    dst = root.joinpath("cricket_scorer")
    #  assert dst.exists(), f"{dst}"
    dst.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(license_header, dst.joinpath("header.txt"))
    dst.joinpath("LICENSE.txt").write_text("\n\n\n\n".join(
        (license_lgplv3.read_text(), license_gplv3.read_text())))
    dst.joinpath("__init__.py").touch(exist_ok=True)


copy_licenses_to_data_dir()

setuptools.setup(
    name="cricket_scorer-arghnews",
    version="0.1.0",
    author="Justin Riddell",
    author_email="arghnews@hotmail.co.uk",
    description="Cricket scoreboard remote controller and MS Excel project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arghnews/cricket_scorer",
    project_urls={},
    package_data=package_data,
    license_files=["LICENSE.txt", "COPYING.LESSER"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Natural Language :: English",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ],
    scripts=["template_gui.py"],

    # include_package_data=True,
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    install_requires=install_requires,
    python_requires=">=3.7",
)
