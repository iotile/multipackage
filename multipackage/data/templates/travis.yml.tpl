jobs:
  include:
    - stage: Test
{% if "macos" in options.test_matrix.platforms %}
      os: osx
      language: sh
      python: "3.6"
      name: "Mac OS - Python 3.6"
      addons:
        homebrew:
          packages:
            - python3
      before_install:
        - python3 -m pip install --upgrade pip wheel virtualenv
        - virtualenv venv -p python3
        - source venv/bin/activate
        - python --version
    - os: osx
      language: sh
      python: "2.7"
      name: "Mac OS - Python 2.7"
      before_install:
        - python -m pip install virtualenv
        - virtualenv venv -p python2
        - source venv/bin/activate
        - python --version
{% endif %}
{% if "windows" in options.test_matrix.platforms %}
    - os: windows
      language: sh
      python: "3.6"
      name: "Windows - Python 3.6"
      before_install:
        - choco install python3 --version 3.6.5
        - export PATH="/c/Python36:/c/Python36/Scripts:$PATH"
        - python -m pip install --upgrade pip wheel virtualenv
        - python --version
    - os: windows
      language: sh
      python: "2.7"
      name: "Windows - Python 2.7"
      before_install:
        - choco install python2
        - export PATH="/c/Python27:/c/Python27/Scripts:$PATH"
        - python -m pip install --upgrade pip wheel
        - python --version
{% endif %}
{% if "linux" in options.test_matrix.platforms %}
    - os: linux
      dist: xenial
      python: "3.6"
      language: python
      name: "Linux - Python 3.6"
    - os: linux
      dist: xenial
      python: "2.7"
      name: "Linux - Python 2.7"
      language: python
{% endif %}

    - stage: "Deploy"
      if: branch = master AND type != pull_request
      script: python .multipackage/scripts/build_documentation.py
      os: linux
      dist: xenial
      python: "3.6"
      language: python
      name: "Documentation to Github Pages"
      deploy:
        - provider: pages
          skip-cleanup: true
          github-token: $GITHUB_TOKEN
          committer-from-gh: true
          keep-history: true
          local-dir: built_docs
{% if repo.iter_context('deploy') | list | length > 0 %}
      env:
{% for name, _value in repo.iter_context('deploy', include_empty=false) %}
        - {{ name | encrypt(only_value=false) }}
{% endfor %}
{% endif %}
    - stage: "Deploy"
      if: tag IS present
      script: python .multipackage/scripts/release_by_name.py $TRAVIS_TAG
      os: linux
      dist: xenial
      python: "3.6"
      language: python
      name: "Release to PyPI Index"
{% if repo.iter_context('deploy') | list | length > 0 %}
      env:
{% for name, _value in repo.iter_context('deploy', include_empty=false) %}
        - {{ name | encrypt(only_value=false) }}
{% endfor %}
{% endif %}
install:
- pip install -r requirements_build.txt -r requirements_doc.txt
{% for _key, component in components|dictsort %}
- pip install {{ component.relative_path }}
{% endfor %}

script:
{% for key, component in components|dictsort %}
- python .multipackage/scripts/test_by_name.py {{ key }}
{% endfor %}
- python .multipackage/scripts/build_documentation.py

notifications:
  email: false
  slack:
    rooms:
    - {{ "SLACK_TOKEN" | encrypt(only_value=true) }}
    template:
    - "Build <%{build_url}|#%{build_number}> (<%{compare_url}|%{commit}>) of %{repository_slug}@%{branch} in PR <%{pull_request_url}|#%{pull_request_number}> by %{author} %{result} in %{elapsed_time}"
    on_success: always
    on_failure: always

