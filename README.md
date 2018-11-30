# CLI Tool for Managing Multi-Package Python Repositories

<!-- MarkdownTOC autolink="true" bracket="round" -->

- [Introduction](#introduction)
- [Basic Usage](#basic-usage)
  - [Required Environment Variables](#required-environment-variables)
  - [Optional Environment Variables](#optional-environment-variables)
- [How It Works](#how-it-works)
- [Frequently Asked Questions](#frequently-asked-questions)
  - [Why Does `multipackage` Exist?](#why-does-multipackage-exist)
  - [Can't You Already Do This?](#cant-you-already-do-this)
  - [Why Isn't `multipackage` More Configurable?](#why-isnt-multipackage-more-configurable)

<!-- /MarkdownTOC -->

## Introduction

This tool is designed to automatically setup or update a github repository that
contains one or more python packages that should be published to a Python Package
Index such as PyPI.  It defaults to a configuration that is suitable for an open
source package published to PyPI.

`multipackage` is packaged as a python package distributed on `PyPI` that
installs a series of script files into your repository to manage
building/testing and releasing it. It includes a console script also named
`multipackage` that can be used to initialize, verify or update these scripts.

Out of the box `multipackage` comes with:

- Well-formatted prose documentation using `sphinx` that is autodeployed to
  GitHub pages every time there is a commit on `master`.
- Cross-platform testing using Travis CI on Python 2.7 and Python 3.6 on Mac,
  Linux and Windows.
- Documentation testing and automatic building as part of the unit test suite.
- Continuous Deployment to PyPI on tagged master releases.  Multiple packages
  per repository are supported and can be released on independent tags.
- Support for repositories containing multiple python packages in a nested
  folder hierarchy.
- Easy updating of repository build scripts with new features by just running
  `multipackage update`.
- Ability to automatically fail the build if the number of linting violations
  have increased (disabled by default).

In order to do all of the above things well, this template is pretty opinionated
in what it assumes your python code will look like.  In particular it currently
makes the following assumptions (i.e. if your python code doesn't work like
this, this template will not work well for you):

- Package testing is performed using `pytest`.
- Package linting is performed using `pylint`.
- Documentation is written in ReST and built into HTML using `sphinx`.
- Packages are to be released to PyPI on Python 2.7 and Python 3.6.
- The CI and CD service will be Travis CI (open-source version)
- Release notes will be tracked per package in a `RELEASE.md` file.


## Basic Usage

> If you need to go beyond what is described here, you should **consult the 
detailed documentation** hosted on [Github Pages](https://iotile.github.io/multipackage).

1. First make sure that you meet the following prerequisites: 
    
    - Your repository must be hosted on GitHub.
    - Your repository must contain 1 or more python packages that you would
      like deployed to PyPI.
    - Your repository must be setup with Travis CI (either org or com).
    - You must be able to support additional files installed into a ` scripts` 
      folder inside your repository.

2. Install `multipackage`, it's compatible with Python 2.7 and Python 3:

    ```
    pip install multipackage
    ```

3. Initialize your repository:

    ```
    multipackage init <path to repository or cwd if blank>
    ```

    This will install a `multipackage.json` and `multipackage_manifest.json` in
    the root of your repository as well as an empty text file at
    `scripts/components.txt`.

    The only required setup step is that you need to fill out `components.txt`
    with names and paths for all of the packages inside your repository that 
    you want to release.  You can have multiple packages per repostiory.

    For the simple case where your repository contains a single package that
    has its `setup.py` file in the root of your repository and works on python
    2 and 3, you could add a line like:

    ```
    package-name-without-spaces: ./, compatibility=universal
    ```

4. Check to make sure you have your environment variables set up correctly:

   ```
   multipackage doctor
   ```

   ```
   multipackage info <path to respository or cwd if blank>
   ```

5. Install (or Update) all of the build scripts based on your `multipackage.json`
   configuration and `components.txt` file:

   ```
   multipackage update
   ```

At this point you are done.  You can immediately test out the documentation
by doing:

```
python scripts/build_documentation.py
```

This will generate sphinx documentation automatically into the `built_docs`
folder.


### Required Environment Variables

In order to set up the CI service correctly and properly encrypt PyPI deployment
credentials, the following environment variables need to be set when you run the
cookie-cutter:

- **PYPI_USER:** The PyPI username you want to use to deploy your package(s) to
  PyPI.
- **PYPI_PASS:** Your PyPI password.  This will be encrypted as a secure
  environment variable and stored in your .travis.yml file.
- **TRAVIS_TOKEN:** An API token for Travis CI.  This is needed to get the RSA
  public key for your target Travis CI project so that we can automatically encrypt
  environment variables into your `.travis.yml` file.
- **GITHUB_TOKEN:** An API token for GitHub with push access to the repository
  so that we can deploy the documentation to github pages.


### Optional Environment Variables

If you want some additional features (like slack notifications), you can also
set the following environment variables:

- **SLACK_WEB_HOOK:** A webhook for your slack workspace if you want a slack
  notification every time a new version of this package is released.


## How It Works

> This section describes the specific details of how `multipackage` sets up a
> repository, what files it installs and how updates work.

The `multipackage` system installs the following directory structure in your
repository:

```
doc/
    <your prose documentation goes here>
    conf.py - Autogenerated sphinx config file that should not be edited
    api/
        <autogenerated api documentation will be put here>

scripts/
    <autogenerated scripts to control the build process>

.pylintrc - Default pylint rules for this project
.travis.yml - Autogenerated Travis CI configuration
.gitignore - A portion of this file is managed by multipackage to exclude files
             that are autogenerated and should not be committed.

multipackage.json - general configuration file for controlling multipackage.
multipackage_manifest.json - manifest file parsed by multipackage

```

It also reserves the following directories for temporary use during builds.  You
need to make sure that you don't use these folders for any other purpose in your
repository:

```
built_docs/
.tmp
```

## Frequently Asked Questions

### Why Does `multipackage` Exist?

Setting up a python repository with good documentation, testing and automatic
releases is tricky to do well.  It's fairly straight-forward to do the basics
like running `tox` for testing and using a hosted CI service to managing
releasing to PyPI, but this leaves a lot of gaps that never seem to get filled
such as:

 - Keeping your API documentation up to date with Sphinx.  Ideally this
   documentation would be automatically generated and deployed as part of the
   build.
 - Managing user onboarding documents like tutorials or HOWTOs.  Often people
   write these as static documents  but they slowly become out of date as the
   underlying code matures.  The result is that the tutorials are 90% right but
   don't work out of the box making it hard for beginners to learn how to use
   your package.  For a new user to your package that has no idea how it's 
   implemented, a HOWTO can either work as-written or no.  Ideally these HOWTOs
   would be continually tested so they always work (and also serve as a nice set
   of integration tests of your package). 
 

### Can't You Already Do This?

Sure, `multipackage` doesn't do anything that fundamentally you could not do 
yourself by wiring together:

- Travis CI
- Appveyor
- ReadTheDocs
- Sphinx
- A few custom scripts to hide all of the pain
- Cookiecutter

Normally, you would do this once and then never touch it again because it's very
fiddly to get working and once it's up and running you don't want to break it
and you're focused on building new features in your package or fixing bugs.

If you like setting up your own CI/CD scripts and you have the time to invest in
getting it just right (and keeping it there), then `multipackage` is probably
not for you.  It was designed for people who are too busy to get a
fully-featured CI system set up or who get frustrated with the amount of time it
takes to debug every little change.

> **Think of `multipackage` as a self-updating cookiecutter that comes with
prebaked best practices.**

### Why Isn't `multipackage` More Configurable?

> **`multipackage` is not intended to be a general purpose library.**  
 
It is a more of a framework rather than a library. If you like the general
outline of what `multipackage` provides, then you can get a lot of
functionality without much configuration.  The trade-off, is that if you don't
like the general outline of what `multipackage` provides, then you're likely
better off starting from scratch (possibly reusing some of the code, possibly
not).

There is not a shortage of great general-purpose tools available to help you
setup modern python package repositories.  **multipackage does not replace those
general purpose tools**.  Instead, it just wires together existing tools in a
specific way that can be automatically installed and maintained.
