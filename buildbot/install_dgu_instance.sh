#!/bin/bash

# This script is for use with the buildbot server, and is used to install the dependencies
# for a particular dgu checkout.

install_dependencies () {
    # Installs DGUs dependencies
    # Takes one argument: the instance name

    instance=$1
    user="ckan$instance"

    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-dgutheme.git@feature-1645-apply-simple-theme#egg=ckanext-dgutheme
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-csw.git@enh-1726-harvesting-model-update#egg=ckanext-csw
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-harvest.git@enh-1726-harvesting-model-update#egg=ckanext-harvest
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-inspire.git@enh-1726-harvesting-model-update#egg=ckanext-inspire
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-spatial.git#egg=ckanext-spatial
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/owslib.git#egg=owslib
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-qa.git#egg=ckanext-qa
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-archiver.git#egg=ckanext-archiver
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-importlib.git#egg=ckanext-importlib
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/datautildate#egg=datautildate
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -r "/var/lib/ckan/$instance/pyenv/src/ckanext-spatial/pip-requirements.txt"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed pastescript
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed carrot

    # Install the qa and archiver dependencies
    sudo apt-get -y install supervisor

    # Configure celeryd under supervisor
    sudo wget -O -  https://raw.github.com/okfn/ckan/master/ckan/config/celery-supervisor.conf | sed \
        -e "/^user/ s/^user=ckan/user=$user/" \
        -e "/^command/ s,/path/to/pyenv/bin/paster,/var/lib/ckan/$instance/pyenv/bin/paster," \
        -e "/^command/ s,/path/to/config/testing.ini,/etc/ckan/$instance/$instance.ini," | tee /etc/supervisor/conf.d/celery-supervisor.conf
}

run_database_migrations () {
    instance=$1
    sudo -u postgres psql -c "UPDATE package_extra SET key = 'UKLP' WHERE key = 'INSPIRE';" "$instance"
    sudo -u postgres psql -c "UPDATE package_extra_revision SET key = 'UKLP' WHERE key = 'INSPIRE';" "$instance"
    sudo -u postgres psql -c "UPDATE resource SET format = NULL where format = 'Unverified';" "$instance"
    sudo -u postgres psql -c "UPDATE resource_revision SET format = NULL where format = 'Unverified';" "$instance"
}

post_install () {
    # Start celeryd and workers under supervisord
    sudo supervisorctl reread
    sudo supervisorctl add celery
    sudo supervisorctl status
}

configure () {
    # Configure the dgu instance.
    # Takes two arguments: the instance name and the domain name

    instance=$1
    domain=$2
    ini_file="/etc/ckan/$instance/$instance.ini"

    # Configures the ini file settings
    sudo sed -e "s/ckan.plugins =.*$/ckan.plugins = dgu_form dgu_theme cswserver harvest gemini_harvester gemini_doc_harvester gemini_waf_harvester inspire_api wms_preview spatial_query qa/" \
             -e "s/^ckan.site_title =.*/ckan.site_title = DGU Release Test/" \
             -e "s/^ckan.site_url =.*/ckan.site_url = http:\/\/$domain/" \
             -e '/^\[app:main\]$/ a\
search.facets = groups tags res_format license resource-type UKLP\
ckan.spatial.srid = 4258\
dgu.xmlrpc_username = CKAN_API\
dgu.xmlrpc_password = XXX\
dgu.xmlrpc_domain = 212.110.177.173\
ckan.enable_call_timing = false' \
             -i.bak "$ini_file"

}
