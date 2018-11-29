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
      script: python scripts/build_documentation.py
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
      env:
        - {{ env.github_token }}
    - stage: "Deploy"
      if: tag IS present
      script: python scripts/release_by_name.py $TRAVIS_TAG
      os: linux
      dist: xenial
      python: "3.6"
      language: python
      name: "Release to PyPI Index"
      env:
        - {{ env.slack_web_hook }}
        - {{ env.pypi_user }}
        - {{ env.pypi_pass }}

install:
- pip install -r requirements_build.txt -r requirements_doc.txt
{% for _key, component in components|dictsort %}
- pip install {{ component.relative_path }}
{% endfor %}

script:
{% for _key, component in components|dictsort %}
- cd {{ component.relative_path }} && pwd && pytest test
{% endfor %}
- python scripts/build_documentation.py

notifications:
  email: false
  slack:
    rooms:
    - {{ env.slack_token }}
    template:
    - "Build <%{build_url}|#%{build_number}> (<%{compare_url}|%{commit}>) of %{repository_slug}@%{branch} in PR <%{pull_request_url}|#%{pull_request_number}> by %{author} %{result} in %{elapsed_time}"
    on_success: always
    on_failure: always

