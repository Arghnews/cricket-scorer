import platform
import setuptools

with open("README.md", "r", encoding = "utf-8") as fh:
    long_description = fh.read()

install_requires = ["PySimpleGUI", "recordclass"]
if platform.system() == "Windows":
    install_requires += ["xlwings"]
else:
    install_requires += ["smbus2"]

setuptools.setup(
    name = "cricket-scorer-arghnews", # Replace with your own username
    version = "0.0.1",
    author = "Justin Riddell",
    author_email = "arghnews@hotmail.co.uk",
    description = "Raspberry pis chicken controller + scoreboard project",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/arghnews/cricket-scorer",
    project_urls = {
    },
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir = {"": "src"},
    packages = setuptools.find_packages(where = "src"),
    install_requires = install_requires,
    python_requires = ">=3.6",
)

