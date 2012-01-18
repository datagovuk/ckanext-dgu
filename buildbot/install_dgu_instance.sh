#!/bin/bash

# This script is for use with the buildbot server, and is used to install the dependencies
# for a particular dgu checkout.

install_dependencies () {
    # Installs DGUs dependencies
    # Takes one argument: the instance name

    instance=$1
    user="ckan$instance"

    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-dgutheme.git@feature-1645-apply-simple-theme#egg=ckanext-dgutheme
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

configure () {
    # Configure the dgu instance.
    # Takes two arguments: the instance name and the domain name

    instance=$1
    domain=$2
    ini_file="/etc/ckan/$instance/$instance.ini"

    # Configures the ini file settings
    sudo sed -e "s/ckan.plugins =.*$/ckan.plugins = dgu_form dgu_theme_embedded cswserver harvest gemini_harvester gemini_doc_harvester gemini_waf_harvester inspire_api wms_preview spatial_query/" \
             -e "s/^ckan.site_title =.*/ckan.site_title = DGU Release Test/" \
             -e "s/^ckan.site_url =.*/ckan.site_url = http:\/\/$domain/" \
             -i.bak "$ini_file"

    echo "ckan.spatial.srid = 4258" | sudo tee -a "$ini_file" > /dev/null
    echo "dgu.xmlrpc_username = CKAN_API" | sudo tee -a "$ini_file" > /dev/null
    echo "dgu.xmlrpc_password = XXX" | sudo tee -a "$ini_file" > /dev/null
    echo "dgu.xmlrpc_domain = 212.110.177.173" | sudo tee -a "$ini_file" > /dev/null
    echo "ckan.enable_call_timing = false" | sudo tee -a "$ini_file" > /dev/null
}
