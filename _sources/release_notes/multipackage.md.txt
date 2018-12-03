# `multipackage` Release Notes

## v0.2.1 (12/2/2018)

- Refactor code to unify all error and warning messages into a generic message
  structure with iter_messages(type) to select warnings or errors.
- Allow templates to declare what environment variables they need based on their
  configured settings.
- Implement `multipackage doctor` to show what environment variables are
  optional or required for a given repository.

## v0.2.0 (12/1/2018)

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
- Add `test_by_name.py` script to handle entering each component subdirectory
  and running the required test commands.
## v0.1.0 (11/29/2018)

- Update location of multipackage files to all live under a `.multipackage`
  directory.  This consolidates everything into a single place and avoids
  cluttering up the repository.  It makes `multipackage` more like `git` in that
  it has a folder that it manages for you and a cli tool that interacts with
  that folder.

## v0.0.1 (11/29/2018)

- Initial commit
