# `multipackage` Release Notes

## HEAD

- Update `ManagedFileSection.ensure_lines` to support matching multiple lines
  with regular expressions so that you can do things like changing the pinned
  version of a given package in a `requirements.txt` file.
- Update `atomic_json` and `render_template` to produce files your native
  line ending by default so that the files are more easily readable on each
  platform (since git checks them out in native line endings anyway).
- Remove Sphinx warnings from `pytest` since they are not fixable and we can't
  move to Sphinx 2.0 anyway because it doesn't support Python 2.7. 
- Move to a template based approach for repository management where each repo
  has a template that installs and configures subsystems.  These subsystems are
  then in charge of managing the repository.  There is one default template
  named `pypi_package` that sets up a repository for releasing pypi packages.

## v0.1.0 (11/29/2018)

- Update location of multipackage files to all live under a `.multipackage`
  directory.  This consolidates everything into a single place and avoids
  cluttering up the repository.  It makes `multipackage` more like `git` in that
  it has a folder that it manages for you and a cli tool that interacts with
  that folder.

## v0.0.1 (11/29/2018)

- Initial commit
