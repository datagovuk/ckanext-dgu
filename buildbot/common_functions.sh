#!/bin/bash

#############################################################
# Common deployment functions
#############################################################
#
# This file contains some functions that are common to the
# various deployments dgu has, and as such is the central
# place to define dependencies etc.  It encompasses both the
# installation of CKAN (as a package install); installation
# of DGU it's dependencies; and also database migrations.
#
# To use this file, just `source` it in your bash script, and
# the function defined in here will be available to your
# script.
#
#############################################################

install_ckan () {
    # Installs CKAN and its dependencies
    # Takes 3 arguments:
    #
    #   $1 : the repository name. e.g. "ckan-1.5.1"
    #   $2 : the instance name. e.g. "std"
    #   $3 : the domain name. e.g. "releasetest.ckan.org"
    #
    # This is only intended to be used once when the server is deployed.

    if [ $# -ne 3 ]
    then
        echo "install_ckan() expects 3 arguments: repo, instance, domain"
        exit 1
    fi

    local repo=$1
    local instance=$2
    local domain=$3

    echo "Updating repositories from http://apt.ckan.org/$repo"
    sudo apt-get update
    sudo apt-get install -y wget
    sudo echo "deb http://apt.ckan.org/$repo lucid universe" | sudo tee /etc/apt/sources.list.d/okfn.list
    sudo wget -qO- "http://apt.ckan.org/packages_public.key" | sudo apt-key add -
    sudo apt-get update

    echo "Installing CKAN and dependencies"
    sudo apt-get install -y ckan postgresql-8.4 solr-jetty postgis postgresql-8.4-postgis rabbitmq-server
    sudo ckan-setup-solr

    echo "Creating new CKAN instance \"$instance\" on \"$domain\""
    sudo ckan-create-instance "$instance" releasetest.ckan.org yes
}

update_ckan () {
    # Upgrades the current CKAN installation (package installation)
    # Takes 1 argument:
    #
    #  $1 : the repository name, eg. "ckan-1.7"
    #
    # This is only intended to be used on a deployment with CKAN already
    # installed.
    #
    # This function will *not* upgrade to a newer version of CKAN, it will
    # only update an existing CKAN installation of the same version.

    local REPO=$1

    echo "Updating repositories from http://apt.ckan.org/$REPO"
    sudo apt-get update
    sudo apt-get upgrade -y
}

install_dgu () {
    # Installs DGU and its dependencies into the python virtual env
    # This function is safe to run if DGU is already installed, it will just
    # update the current installation.

    # Modify this to change dgu's dependencies.

    local instance=$1
    local branch=$2
    local user="ckan$instance"

    sudo apt-get install -y mercurial git-core
    
    echo "Installing DGU plugin dependencies for instance \"$instance\""
    
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-dgu.git@$branch#egg=ckanext-dgu"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-csw.git#egg=ckanext-csw"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-harvest.git#egg=ckanext-harvest"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-inspire.git#egg=ckanext-inspire"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-spatial.git#egg=ckanext-spatial"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/owslib.git#egg=owslib"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-qa.git#egg=ckanext-qa"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-archiver.git#egg=ckanext-archiver"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/ckanext-importlib.git#egg=ckanext-importlib"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://github.com/okfn/datautildate#egg=datautildate"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed -e "git+https://bitbucket.org/dread/ckanext-os.git#egg=ckanext-os"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed GeoAlchemy==0.6
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M -r "/var/lib/ckan/$instance/pyenv/src/ckanext-spatial/pip-requirements.txt"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed pastescript
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install -M --ignore-installed carrot

    # Install the qa and archiver dependencies
    sudo apt-get -y install supervisor

    # Configure celeryd under supervisor
    echo "Configuring celeryd to run under supervisor"
    sudo wget -O -  https://raw.github.com/okfn/ckan/master/ckan/config/celery-supervisor.conf | sed \
        -e "/^user/ s/^user=ckan/user=$user/" \
        -e "/^\[program:celery\]/ s/^\[program:celery\]/[program:celery-$instance]/" \
        -e "/^command/ s,/path/to/pyenv/bin/paster,/var/lib/ckan/$instance/pyenv/bin/paster," \
        -e "/^command/ s,/path/to/config/testing.ini,/etc/ckan/$instance/$instance.ini," | tee /etc/supervisor/conf.d/celery-supervisor-$instance.conf

    # Configure the harvest fetcher and gatherers to run under supervisor
    echo "Configuring harvesters to run under supervisor"
    sudo cat "/var/lib/ckan/$instance/pyenv/src/ckanext-harvest/config/supervisor/ckan_harvesting.conf" | sed \
        -e "/^user/ s/^user=ckan/user=$user/" \
        -e "/^\[program:ckan_gather_consumer\]/ s/^\[program:ckan_gather_consumer\]/[program:ckan_gather_consumer-$instance]/" \
        -e "/^\[program:ckan_fetch_consumer\]/ s/^\[program:ckan_fetch_consumer\]/[program:ckan_fetch_consumer-$instance]/" \
        -e "/^command/ s,/path/to/pyenv/bin/paster,/var/lib/ckan/$instance/pyenv/bin/paster," \
        -e "/^command/ s,/path/to/config/$instance.ini,/etc/ckan/$instance/$instance.ini," | tee /etc/supervisor/conf.d/ckan_harvesting-$instance.conf

    # Link to the solr schema file
    echo "Replacing solr schema file"
    sudo /etc/init.d/jetty stop

    # Backup ckan original file if it doesn't already have a backup
    if [[ ! -f /etc/solr/conf/schema.xml.ckan ]];
    then
        sudo mv /etc/solr/conf/schema.xml /etc/solr/conf/schema.xml.ckan
    fi

    sudo cp "/var/lib/ckan/$instance/pyenv/src/ckanext-dgu/config/solr/schema-1.4-dgu.xml" /etc/solr/conf/schema.xml
    sudo /etc/init.d/jetty start
}

configure () {
    # Configure the dgu instance.
    #
    # Takes three arguments: the instance name, the domain name, xmlrpc password
    #
    # This can be run on an already deployed instance to update the config files.

    local instance=$1
    local domain=$2
    local xmlrpc_password=$3
    local ini_file="/etc/ckan/$instance/$instance.ini"

    sudo mv "/etc/ckan/$instance/who.ini" "/etc/ckan/$instance/who.ini.bak"
    sudo ln -s "/var/lib/ckan/$instance/pyenv/src/ckanext-dgu/ckanext/dgu/who.ini" "/etc/ckan/$instance/who.ini"

    # Some entries in who.ini (which lives in /etc/ckan), expect to be in /var/lib/ckan/$instance
    sudo sed -e "s,%(here),/var/lib/ckan/$instance,g" -i "/etc/ckan/$instance/who.ini"

    # Configures the ini file settings
    sudo sed -e "s/ckan.plugins =.*$/ckan.plugins = dgu_publisher_form dgu_publishers dgu_drupal_auth dgu_auth_api dgu_form dgu_theme cswserver harvest gemini_harvester gemini_doc_harvester gemini_waf_harvester inspire_api spatial_query qa synchronous_search dgu_search dgu_dataset_form spatial_metadata dataset_extent_map os_search os_preview/" \
             -e "s/^ckan.site_title =.*/ckan.site_title = DGU - $instance/" \
             -e "s/^ckan.site_url =.*/ckan.site_url = http:\/\/$domain/" \
             -e "s/^ckan.gravatar_default =.*/ckan.gravatar_default = mm/" \
\
             -e "s/^openid_enabled = .*//" \
             -e "s/^dgu.admin.name = .*//" \
             -e "s/^dgu.admin.email = .*//" \
             -e "s/^search.facets = .*//" \
             -e "s/^ckan.spatial.srid = .*//" \
             -e "s/^dgu.xmlrpc_username = .*//" \
             -e "s/^dgu.xmlrpc_password = .*//" \
             -e "s/^dgu.xmlrpc_domain = .*//" \
             -e "s/^ckan.enable_call_timing = .*//" \
             -e "s/^ckan.datasets_per_page = .*//" \
             -e "s/^ckan.spatial.dataset_extent_map.routes = .*//" \
             -e "s/^ckan.spatial.dataset_extent_map.map_type = .*//" \
\
             -e '/^\[app:main\]$/ a\
openid_enabled = False\
dgu.admin.name = Test Account\
dgu.admin.email = david.read@hackneyworkshop.com\
search.facets = groups tags res_format license resource-type UKLP license_id-is-ogl publisher\
ckan.spatial.srid = 4258\
dgu.xmlrpc_username = CKAN_API\
dgu.xmlrpc_password = $xmlrpc_password\
dgu.xmlrpc_domain = $domain\
ckan.enable_call_timing = false\
ckan.datasets_per_page = 10\
ckan.spatial.dataset_extent_map.routes = ckanext.dgu.controllers.package:PackageController/read\
ckan.spatial.dataset_extent_map.map_type = os\
' \
             -i.bak "$ini_file"

}

flush_database () {
    # Wipes and rebuilds the database from a pg_dump file located at /home/okfn/dgu_live.pg_dump
    #
    # Requires 1 argument: the ckan instance name
    
    if [ $# -ne 3 ]
    then
        echo "restore_database() expects 3 arguments: instance dump-fil-location users-file-location"
        exit 1
    fi

    # Just make sure apache isn't running, it shouldn't be
    sudo /etc/init.d/apache2 stop

    local dump_file=$2
    if [ ! -e $dump_file ]
    then
        echo "Can't restore database, dumpfile does not exist: $dump_file"
        exit 1
    fi

    local users_file=$3
    if [ ! -e $users_file ]
    then
      echo "Can't restore database, users file does not exist: $users_file"
      exit 1
    fi

    local instance=$1
    local user="ckan$instance"
    local ini_file="/etc/ckan/$instance/$instance.ini"

    echo "Restoring database for instance \"$instance\""

    sudo -u postgres dropdb "$instance"
    sudo -u postgres createdb "$instance"
    sudo -u postgres createlang plpgsql "$instance"

    sudo sed -e "s/Owner: dgu/Owner: $instance/g" \
        -e "s/OWNER\(.*\)dgu/OWNER\1$instance/g" \
        -e "/^REVOKE ALL ON TABLE/ s/dgu;$/$instance;/" \
        -e "/^GRANT ALL ON TABLE/ s/dgu;$/$instance;/" \
        $dump_file | sudo -u postgres psql "$instance" -f -

    # do_pgtune
    # Tunes the postgres configuration.
    sudo apt-get install -y pgtune
    pgtune -i /etc/postgresql/8.4/main/postgresql.conf | sudo tee -a /etc/postgresql/8.4/main/postgresql.conf
    local old_shmmax=`cat /proc/sys/kernel/shmmax`
    sudo sysctl -w kernel.shmmax=3355443200 # fairly arbitrary
    sudo /etc/init.d/postgresql-8.4 restart

    # Hacky workaround prior to running db upgrade:
    # The harvest plugin is mis-behaving, and creates db tables if they don't exist when imported.
    # The workaround is to remove the installed plugins from the .ini file; run the upgrade; reinstate the plugins
    sudo sed -e "s/^ckan\.plugins = \(.*\)/ckan.plugins = \n##ckan.plugins = \1/" -i $ini_file

    # Run the upgrade
    echo "Upgrading the database..."
    sudo -u "$user"  "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan db upgrade --config="/etc/ckan/$instance/$instance.ini"

    # Undo the .ini file hack above
    sudo sed -e "/^ckan\.plugins = $/ d" \
             -e "s/^##ckan\.plugins = \(.*\)/ckan.plugins = \1/" -i $ini_file

    # Undo the pgtune tweaks
    sudo sysctl -w kernel.shmmax=$old_shmmax
    sudo sed -e "/# pgtune wizard/ d" -i.bak /etc/postgresql/8.4/main/postgresql.conf
    sudo /etc/init.d/postgresql-8.4 restart

    echo "Running database migrations...."

    sudo -u postgres psql -c "UPDATE package_extra SET key = 'UKLP' WHERE key = 'INSPIRE';" "$instance"
    sudo -u postgres psql -c "UPDATE package_extra_revision SET key = 'UKLP' WHERE key = 'INSPIRE';" "$instance"
    sudo -u postgres psql -c "UPDATE resource SET format = NULL where format = 'Unverified';" "$instance"
    sudo -u postgres psql -c "UPDATE resource_revision SET format = NULL where format = 'Unverified';" "$instance"

    local pyenv_root="/var/lib/ckan/$instance/pyenv"
    "$pyenv_root/bin/python" "$pyenv_root/src/ckanext-dgu/ckanext/dgu/bin/import_publishers.py" "/etc/ckan/$instance/$instance.ini" "$pyenv_root/src/ckanext-dgu/buildbot/fixtures/dgupub.csv"
    "$pyenv_root/bin/python" "$pyenv_root/src/ckanext-dgu/ckanext/dgu/bin/publisher_datasets_assoc.py" "/etc/ckan/$instance/$instance.ini" "$pyenv_root/src/ckanext-dgu/buildbot/fixtures/nodepublishermap.csv" | sudo -u postgres psql "$instance"
    "$pyenv_root/bin/python" "$pyenv_root/src/ckanext-dgu/ckanext/dgu/bin/user_import.py" "/etc/ckan/$instance/$instance.ini" "$pyenv_root/src/ckanext-dgu/buildbot/fixtures/nodepublishermap.csv" "$users_file"

    echo "Tidying resource formats..."
    "$pyenv_root/bin/python" "$pyenv_root/src/ckanext-dgu/ckanext/dgu/bin/tidy_resource_types.py" --config "/etc/ckan/$instance/$instance.ini"
    echo "Finished tidying resource formats."
}

create_test_admin_user () {

    local $instance = $1
    local user="ckan$instance"

    echo "Creating admin user"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan user add test_admin password=password --config=/etc/ckan/$instance/$instance.ini
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan sysadmin add test_admin --config=/etc/ckan/$instance/$instance.ini
    echo "Finished creating admin user"
}

post_install () {

    local instance=$1
    local user="ckan$instance"

    # Start celeryd and workers under supervisord
    echo "Starting post-installation processes."
    sudo supervisorctl reread
    sudo supervisorctl add "celery-$instance"
    sudo supervisorctl add "ckan_gather_consumer-$instance"
    sudo supervisorctl add "ckan_fetch_consumer-$instance"
    sudo supervisorctl status

    echo "*/15 *  *   *   *     /var/lib/ckan/$instance/pyenv/bin/paster --plugin=ckanext-harvest harvester run --config=/etc/ckan/$instance/$instance.ini" | tee -a "/var/spool/cron/crontabs/$user"
    sudo service cron reload
}

restart_apache () {
    sudo /etc/init.d/apache2 restart
}

rebuild_search_index () {
    local instance=$1
    local user="ckan$instance"
    echo "Rebuilding the index in the background..."
    nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan search-index rebuild --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/solr_output.log &
    echo "Started the indexer"
}

start_harvest_import_daemon () {
    local instance=$1
    local user="ckan$instance"
    echo "Starting the harvester import in the background..."
    nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckanext-harvest harvester import --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/harvester_output.log &
    echo "Started the import"
}

start_qa_daemon () {
    local instance=$1
    local user="ckan$instance"
    echo "Starting the qa update in the background..."
    nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckanext-qa qa update --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/qa_output.log &
    echo "Started the update"
}

## install_ckan $REPO $INSTANCE $DOMAIN
## install_dgu $INSTANCE $BRANCH
## restore_database $INSTANCE
## configure_ini_file $INSTANCE $DOMAIN
## create_test_admin_user $INSTANCE
## 
## # source the particular checkout's dependency post-installation function, post_install()
## source "/var/lib/ckan/$INSTANCE/pyenv/src/ckanext-dgu/buildbot/install_dgu_instance.sh"
## post_install $INSTANCE
## 
## restart_apache
## 
## echo "Rebuilding the index in the background..."
## nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan search-index rebuild --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/solr_output.log &
## echo "Started the indexer"
## echo "Starting the harvester import in the background..."
## nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckanext-harvest harvester import --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/harvester_output.log &
## echo "Started the import"
## 
## echo "Starting the qa update in the background..."
## nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckanext-qa qa update --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/qa_output.log &
## echo "Started the update"
