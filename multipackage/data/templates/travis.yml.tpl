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
      sudo: false
      python: "3.6"
      language: python
      name: "Linux - Python 3.6"
    - os: linux
      dist: xenial
      sudo: false
      python: "2.7"
      name: "Linux - Python 2.7"
      language: python
{% endif %}

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
  on_success: always
  on_failure: always
  email: false
  slack:
    secure: fTxYi+g7KKlH8Hhs+r+A7FVoj00J1N2IawIZZNB2L6MSB2/puTL3QKOVF5IprvwKcc2lhAe3dPMinhDYgoBY0AeibaEb4GFf7pGJhnN03sdxTBWMBswePf5eU4dexdpdAMldsqffMDbd7Uo22+j0/k0RhJhX7nTvu4GbUFtv4Gh0yh2nw5dDcD3y4ZLRk1SOAK8xErBZO8x30PNPZze+pjIyVcxfkOE1x2P/TfkY1bkWLDbts5bV4txb0Ycu14uS7lWE7OJvxOltl7fBVLnoCrD36fEtdlQes/ZtRqBQJAbDEXtjCHiJDIm83DY2Oh+hrYKrtIFllfYUlNn+gZM9Z3AWtv6zKYKR18XtK+TqI+NUJrAjsgECgy+RmrP2n2DDnYEFePI3YAAet5ssFv0RkE/+7eJpHZFr8mAopyWFhuxUPnnYHVwwTDMk7XFIGx6DCvjH/NDBgFpEXTfZlJ8E0xscPcUIsHr5B6k6FEZa4Dcyoae6OJ2lYVpHu+MPwA2ohGyaxF02HwLRD2ZGfczWEUTYsbexcV91+GyW/SuJHSAUE78fNu8P/WzX5LwBlmcvczTKwpYj52co5K2r6embQ2WcH0qt2GqBfkQFOl2eP00AgIjyJ9MXJD9Ai9YBbU1585jI6MZ0RYt4HZQsujQhHVSgTf1sy5wEDbhPUgiZ12o=
