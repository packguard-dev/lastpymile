# lastjsmile
# `LastJSMile`: Identify the differences between build artifacts of NPM packages and the respective source code repository

The tool analyzes a package from the [NPM](https://www.npmjs.com/) repository.


## Features
 - Retrieve the Github URL of a NPM package
 - Identify the differences between build artifacts of software packages and the respective source code repository

## Installation
*Requires python 3.7+*

- Suggested: Install venv and create virtual environment
```bash
python -m venv lastjsmile
# Activate venv in Windows
venv/Scripts/activate.bat
# Activate venv in Linux
source lastjsmile/bin/activate
```
- Install required packages
```bash
python -m pip install -r requirements.txt
```

## Usage
To list all available options
```bash
cd src/
python -m lastpymile_npm.main -h
```
To scan a package:
```bash
cd src/
python -m lastpymile_npm.main <package_name>[:<package_version>] [-l <github_link>] [-a <local_artifact>]
```
Example (for package "meow"):
```bash
python -m lastpymile_npm.main meow
```

## Limitations
- Binary distributions (e.g., .exe, .dmg) are not supported
- Packages that are not hosted on Github are not supported yet.

