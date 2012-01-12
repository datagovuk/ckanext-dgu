#!/bin/bash

# This script is for use with the buildbot server, and is used to install the dependencies
# for a particular dgu checkout.

install_dependencies () {
    # Installs DGUs dependencies
    # Takes one argument: the instance name

    instance=$1
    user="ckan$instance"

    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-csw.git#egg=ckanext-csw
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-harvest.git#egg=ckanext-harvest
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-inspire.git#egg=ckanext-inspire
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-spatial.git#egg=ckanext-spatial
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/owslib.git#egg=owslib
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-qa.git#egg=ckanext-qa
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-importlib.git#egg=ckanext-importlib
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/datautildate#egg=datautildate
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -r "/var/lib/ckan/$instance/pyenv/src/ckanext-spatial/pip-requirements.txt"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed pastescript
}
