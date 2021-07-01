import pathlib
import setuptools

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

package_data = {
    "license": ["LICENSE.txt", "COPYING.LESSER",],
    "icon": ["cricket.ico",],
    "third_party_licenses": [str(d) for d in pathlib.Path("3rd party licenses").rglob("*.txt")],
}

# yapf: enable

# if platform.system() == "Windows":
#     install_requires += ["xlwings"]
# else:
#     install_requires += ["smbus2"]

setuptools.setup(
    name="cricket-scorer-arghnews",
    version="0.1",
    author="Justin Riddell",
    author_email="arghnews@hotmail.co.uk",
    description="Cricket scoreboard remote controller and MS Excel project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arghnews/cricket-scorer",
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
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    install_requires=install_requires,
    python_requires=">=3.7",
)
