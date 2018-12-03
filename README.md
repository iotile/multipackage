# A Tool for Sharing Best-Practice CI/CD Templates

<!-- MarkdownTOC autolink="true" bracket="round" -->

- [Introduction](#introduction)
- [Usage - Default PyPI Template](#usage---default-pypi-template)
  - [Installation](#installation)
  - [Using the Installed Scripts](#using-the-installed-scripts)
  - [Updating Your Repository](#updating-your-repository)
  - [Handling Secrets](#handling-secrets)
  - [Required Environment Variables](#required-environment-variables)
  - [Optional Environment Variables](#optional-environment-variables)
- [How It Works](#how-it-works)
- [Frequently Asked Questions](#frequently-asked-questions)
  - [Why Does `multipackage` Exist?](#why-does-multipackage-exist)
  - [Can't You Already Do This?](#cant-you-already-do-this)
  - [Why Isn't `multipackage` More Configurable?](#why-isnt-multipackage-more-configurable)

<!-- /MarkdownTOC -->

## Introduction

`multipackage` is a tool that works like a self-updating `cookiecutter`.  It
configures a code repository (such as one hosted on GitHub) according to a
template.  An example template could be setting up a Github Repository that
contains 3 related python packages distributed on PyPI with Cross-Platform
Continuous Integration on Travis CI, API documentation on GitHub pages and
Continuous Deployment to PyPi on tagged commits.

`multipackage` is very good at setting up repositories for Continuous
Integration and Continuous Deployment. Unlike many other tools that achieve a
similar goal, such as Starter Templates from the javascript ecosystem or
`cookiecutters`, `multipackage` templates are designed to be easily updated once
installed using the `multipackage` command line tool and can contain complex
setup logic.

>Currently, `multipackage` is restricted with working with Python based
>repositories, but that is not inherent in the design and it will support other
>repositories in the future.

`multipackage` is distributed as an open-source python package on `PyPI`.  It is
designed to support third-party templates much like the popular `cookiecutter`
project but it also includes a template for python based repositories as an
example of how the package can be used.


## Usage - Default PyPI Template

Out of the box `multipackage` comes with a prebuilt template for python-based
repositories hosted on GitHub that includes:

- Well-formatted prose documentation using `sphinx` that is autodeployed to
  GitHub pages every time there is a commit on `master`.
- Cross-platform testing using Travis CI on Python 2.7 and Python 3.6 on Mac,
  Linux and Windows.
- Documentation testing and automatic building as part of the unit test suite.
  Integration tests can be included as embedded examples inside the
  documentation.
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


### Installation

> If you need to go beyond what is described here, you should **consult the 
detailed documentation** hosted on [Github Pages](https://iotile.github.io/multipackage).

1. First make sure that you meet the following prerequisites: 
    
    - Your repository must be hosted on GitHub.
    - Your repository must contain 1 or more python packages that you would
      like deployed to PyPI.
    - Your repository must be setup with Travis CI (either org or com).

2. Install `multipackage`, it's compatible with Python 2.7 and Python 3:

    ```
    pip install --upgrade multipackage
    ```

3. Initialize your repository:

    ```
    multipackage init [path to repository, defaults to cwd]
    ```

    This will install a `.multipackage` folder with three files:
    
    ```
    .multipackage/
        settings.json
        manifest.json
        components.txt
    ```

    The only required setup step is that you edit `components.txt` with names
    and paths for all of the packages inside your repository that you want to
    release.  You can have multiple packages per repository if you want.

    For the simple case where your repository contains a single package that
    has its `setup.py` file in the root of your repository and works on python
    2 and 3, you could add a line like:

    ```
    project-identifier-without-spaces: ./
    ```

    The project identifier can be any combination of letters, numbers, or `_`
    characters without whitespace.  It will be used to identify `git` tags that
    designate releases as well as to distinguish different sub-folders of your
    repository that correspond with different packages (if you have more than
    one package per repository).

4. Check to make sure you have your environment variables set up correctly:

   ```
   multipackage doctor [path to repository, defaults to cwd]
   ```

   ```
   multipackage info [path to repository, defaults to cwd]
   ```

5. Install (or Update) all of the build scripts based on your `multipackage.json`
   configuration and `components.txt` file:

   ```
   multipackage update [path to repository, defaults to cwd]
   ```

At this point, installation is done.  You can immediately test out the
documentation by doing:

```
pip install -r requirements_build.txt -r requirements_doc.txt
python .multipackage/scripts/build_documentation.py
```

This will generate html-based sphinx documentation automatically into the
`built_docs` directory.

### Using the Installed Scripts

Once you run `multipage update`, you will get a series of helper scripts
installed into the `.multipackage/scripts` directory.  These scripts will be
referenced during the CI process by e.g. your `.travis.yml` file to
automatically built, test and deploy your packages, but you can also invoke
them yourself.  The key scripts included with the `pypi_package` template are:

- `build_documentation.py`: This script will produce
  html documentation for your repository in the `built_docs` folder.

- `release_notes.py`: View and verify the release notes for each package in 
  your repository.

- `test_by_name.py PACKAGE`: Run tests on the given package in your repository.

- `release_by_name.py PACKAGE`: Release (or test the release process) for a 
  given package in your repository.

- `tag_release.py PACKAGE-VERSION`: Run pre-release sanity checks and then push
  a `git tag` to trigger a Travis CI build that will release your package to
  PyPI.

### Updating Your Repository

At any time, you can ensure that you have the latest version of your template
installed by running:

```
multipackage update
```

This operation is idempotent and vcs friendly with easy to understand diffs.  It
is always safe to run `multipackage update`.  

**The `multipackage` python distribution is not used by any of the scripts
installed into your repository and the installed scripts only change when you
call `multipackage update`.**  

You should never have to worry about checking what version of `multipackage` you
have installed or having your release process break because someone was using an
older or newer version of `multipackage` on their machine.

### Handling Secrets

When `multipackage update` is called, any required secrets needed for deploying
your packages are pulled from environment variables and encrypted into your
`.travis.yml` file.  You can find the list of all required and optional 
environment variables by running:

```
multipackage info [path to repository, defaults to cwd]
```

### Required Environment Variables

In order to set up the CI service correctly and properly encrypt PyPI deployment
credentials, the following environment variables need to be set when you run 
`multipackage update` with the default `pypi_package` template:

- **PYPI_USER:** The PyPI username you want to use to deploy your package(s) to
  PyPI.
- **PYPI_PASS:** Your PyPI password.  This will be encrypted as a secure
  environment variable and stored in your .travis.yml file.
- **TRAVIS_TOKEN:** An API token for Travis CI.  This is needed to get the RSA
  public key for your target Travis CI project so that we can automatically
  encrypt environment variables into your `.travis.yml` file.
- **GITHUB_TOKEN:** An API token for GitHub with push access to the repository
  so that we can deploy the documentation to github pages.


### Optional Environment Variables

If you want some additional features (like slack notifications), you can also
set the following environment variables:

- **SLACK_WEB_HOOK:** A webhook for your slack workspace if you want a slack
  notification every time a new version of this package is released.
- **SLACK_TOKEN:** A Travis CI slack token for notifying a slack channel every
  time a build succeeds or fails.


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

.multipackage/
    scripts/
        <autogenerated scripts to control the build process>
    settings.json - general configuration file for controlling multipackage.
    manifest.json - manifest file parsed by multipackage
    components.txt - A list of all of the subdirectories in your repository that
                     contain separate projects.

.pylintrc - Default pylint rules for this project
.travis.yml - Autogenerated Travis CI configuration
.gitignore - A portion of this file is managed by multipackage to exclude files
             that are autogenerated and should not be committed.
```

It also reserves the following directories for temporary use during builds.  You
need to make sure that you don't use these folders for any other purpose in your
repository:

```
built_docs/
.tmp_docs
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
   implemented, a HOWTO either works as-written or not.  Ideally these HOWTOs
   would be continually tested so they always work (and also serve as a nice set
   of integration tests of your package).

 - Proper unit and integration testing of the build and release scripts. Usually
   these are somewhat hacky one-off scripts that never receive the same kind of
   attention to testing and craft as the rest of the codebase.  Consequently
   they can often be fragile sources of failure at the worst possible moment
   that are difficult and time-consuming to debug.

### Can't You Already Do This?

Sure, `multipackage` doesn't do anything that fundamentally you could not do 
yourself by wiring together:

- Travis CI
- Appveyor
- ReadTheDocs
- Sphinx
- A few custom scripts
- Cookiecutter

Normally, you would do this once and then never touch it again because it's very
fiddly to get working and once it's up and running you want to focus on building
new features in your package or fixing bugs.

If you like setting up your own CI/CD scripts and you have the time to invest in
getting it just right (and keeping it there), then `multipackage` is probably
not for you.  It is designed for people who are too busy to get a fully-featured
CI system set up or who get frustrated with the amount of time it takes to debug
every little change.

> **Think of `multipackage` as a self-updating cookiecutter that comes with
pre-baked best practices.**

### Why Isn't `multipackage` More Configurable?

> **`multipackage` is not intended to be a general purpose library.**  

It is a more of a framework than a library. If you like the general outline of
what a `multipackage` template provides, then you can get a lot of functionality
without much configuration.  The trade-off is that if you don't like the general
outline of what a `multipackage` template provides, then you're likely better
off starting from scratch and building your own template (or just rolling your
own solution without `multipackage`).

The goal of `multipackage` is to encourage the sharing of best-practices so it
is designed around the concept of a complete template for a given type of
repository that has a small set of configurable options rather than an a la
carte set of features that users can pick and choose from.

There is not a shortage of great general-purpose tools available to help you
setup modern code repositories with automated builds and testing. 

**multipackage does not replace those general purpose tools**.  Instead, it just
helps wire those existing tools together in specific ways that can be
automatically installed and maintained.
