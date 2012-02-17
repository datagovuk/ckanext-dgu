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
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-archiver.git#egg=ckanext-archiver
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-importlib.git#egg=ckanext-importlib
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/datautildate#egg=datautildate
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -r "/var/lib/ckan/$instance/pyenv/src/ckanext-spatial/pip-requirements.txt"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed pastescript
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed carrot

    # Install the qa and archiver dependencies
    sudo apt-get -y install supervisor

    # Configure celeryd under supervisor
    echo "Configuring celeryd to run under supervisor"
    sudo wget -O -  https://raw.github.com/okfn/ckan/master/ckan/config/celery-supervisor.conf | sed \
        -e "/^user/ s/^user=ckan/user=$user/" \
        -e "/^command/ s,/path/to/pyenv/bin/paster,/var/lib/ckan/$instance/pyenv/bin/paster," \
        -e "/^command/ s,/path/to/config/testing.ini,/etc/ckan/$instance/$instance.ini," | tee /etc/supervisor/conf.d/celery-supervisor.conf

    # Configure the harvest fetcher and gatherers to run under supervisor
    echo "Configuring harvesters to run under supervisor"
    sudo cat "/var/lib/ckan/$instance/pyenv/src/ckanext-harvest/config/supervisor/ckan_harvesting.conf" | sed \
        -e "/^user/ s/^user=ckan/user=$user/" \
        -e "/^command/ s,/path/to/pyenv/bin/paster,/var/lib/ckan/$instance/pyenv/bin/paster," \
        -e "/^command/ s,/path/to/config/$instance.ini,/etc/ckan/$instance/$instance.ini," | tee /etc/supervisor/conf.d/ckan_harvesting.conf

    # Link to the solr schema file
    echo "Replacing solr schema file"
    sudo /etc/init.d/jetty stop
    sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.ckan
    sudo ln -s "/var/lib/ckan/$instance/pyenv/src/ckanext-dgu/config/solr/schema-1.3-dgu.xml" /etc/solr/conf/schema.xml
    sudo /etc/init.d/jetty start
}

run_database_migrations () {
    instance=$1
    sudo -u postgres psql -c "UPDATE package_extra SET key = 'UKLP' WHERE key = 'INSPIRE';" "$instance"
    sudo -u postgres psql -c "UPDATE package_extra_revision SET key = 'UKLP' WHERE key = 'INSPIRE';" "$instance"
    sudo -u postgres psql -c "UPDATE resource SET format = NULL where format = 'Unverified';" "$instance"
    sudo -u postgres psql -c "UPDATE resource_revision SET format = NULL where format = 'Unverified';" "$instance"

    pyenv_root="/var/lib/ckan/$instance/pyenv"
    "$pyenv_root/bin/python" "$pyenv_root/src/ckanext-dgu/ckanext/dgu/bin/import_publishers.py" "/etc/ckan/$instance/$instance.ini" "$pyenv_root/src/ckanext-dgu/buildbot/fixtures/dgupub.csv"

}

post_install () {

    instance=$1
    user="ckan$instance"

    # Start celeryd and workers under supervisord
    echo "Starting post-installation processes."
    sudo supervisorctl reread
    sudo supervisorctl add celery
    sudo supervisorctl add ckan_gather_consumer
    sudo supervisorctl add ckan_fetch_consumer
    sudo supervisorctl status

    echo "*/15 *  *   *   *     /var/lib/ckan/$instance/pyenv/bin/paster --plugin=ckanext-harvest harvester run --config=/etc/ckan/$instance/$instance.ini" | tee -a "/var/spool/cron/crontabs/$user"
}

configure () {
    # Configure the dgu instance.
    # Takes two arguments: the instance name and the domain name

    instance=$1
    domain=$2
    ini_file="/etc/ckan/$instance/$instance.ini"

    # Configures the ini file settings
    sudo sed -e "s/ckan.plugins =.*$/ckan.plugins = publisher_form dgu_publishers dgu_auth_api dgu_form dgu_theme cswserver harvest gemini_harvester gemini_doc_harvester gemini_waf_harvester inspire_api wms_preview spatial_query qa synchronous_search dgu_search/" \
             -e "s/^ckan.site_title =.*/ckan.site_title = DGU Release Test/" \
             -e "s/^ckan.site_url =.*/ckan.site_url = http:\/\/$domain/" \
             -e "s/^ckan.gravatar_default =.*/ckan.gravatar_default = mm/" \
             -e '/^\[app:main\]$/ a\
dgu.admin.name = Test Account\
dgu.admin.email = ross.jones@okfn.org\
search.facets = groups tags res_format license resource-type UKLP license_id-is-ogl\
ckan.spatial.srid = 4258\
dgu.xmlrpc_username = CKAN_API\
dgu.xmlrpc_password = XXX\
dgu.xmlrpc_domain = 212.110.177.173\
ckan.enable_call_timing = false' \
             -i.bak "$ini_file"

}
