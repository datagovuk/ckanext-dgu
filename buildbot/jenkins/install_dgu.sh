#!/bin/bash

if [ $# -ne 4 ]
then
    echo "Usage: `basename $0` repo-name ckan-instance-name domain dgu-branch"
    echo
    echo "eg: `basename $0` ckan-1.5.1 std releasetest.ckan.org master"
    exit 1
fi

REPO=$1
INSTANCE=$2
DOMAIN=$3
BRANCH=$4

install_ckan () {
    # Installs CKAN and its dependencies
    # Takes 3 arguments:
    #
    #   $1 : the repository name. e.g. "ckan-1.5.1"
    #   $2 : the instance name. e.g. "std"
    #   $3 : the domain name. e.g. "releasetest.ckan.org"

    if [ $# -ne 3 ]
    then
        echo "install_ckan() expects 3 arguments: repo, instance, domain"
        exit 1
    fi

    repo=$1
    instance=$2
    domain=$3

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

install_dgu () {
    # Installs DGU and its dependencies into the python virtual env

    instance=$1
    branch=$2
    user="ckan$instance"

    sudo apt-get install -y mercurial git-core
    
    echo "Installing DGU plugin dependencies for instance \"$instance\""
    
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e "git+https://github.com/okfn/ckanext-dgu.git@$branch#egg=ckanext-dgu"

    # source the particular checkout's dependency installation function, install_dependencies()
    source "/var/lib/ckan/$instance/pyenv/src/ckanext-dgu/buildbot/install_dgu_instance.sh"

    # ... and call it
    install_dependencies $instance

    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-csw.git#egg=ckanext-csw
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-harvest.git#egg=ckanext-harvest
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-inspire.git#egg=ckanext-inspire
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-spatial.git#egg=ckanext-spatial
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/owslib.git#egg=owslib
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-qa.git#egg=ckanext-qa
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/ckanext-importlib.git#egg=ckanext-importlib
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -e git+https://github.com/okfn/datautildate#egg=datautildate
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed -r "/var/lib/ckan/$instance/pyenv/src/ckanext-spatial/pip-requirements.txt"
    ## sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/pip" install --ignore-installed pastescript
}

configure_ini_file () {

    if [ $# -ne 2 ]
    then
        echo "configure_ini_file() expects 2 arguments: instance, domain"
        exit 1
    fi

    instance=$1
    domain=$2
    ini_file="/etc/ckan/$instance/$instance.ini"

    echo "Configuring ini file"

    # source the checkout's installation file for the configure() function
    source "/var/lib/ckan/$instance/pyenv/src/ckanext-dgu/buildbot/install_dgu_instance.sh"
    configure $instance $domain


    # Configures the ini file settings
    ## sudo sed -e "s/ckan.plugins =.*$/ckan.plugins = dgu_form_api cswserver harvest gemini_harvester gemini_doc_harvester gemini_waf_harvester inspire_api wms_preview spatial_query/" \
    ##          -e "s/^ckan.site_title =.*/ckan.site_title = DGU Release Test/" \
    ##          -e "s/^ckan.site_url =.*/ckan.site_url = http://$domain/" \
    ##          -i.bak "$ini_file"

    ## echo "ckan.spatial.srid = 4258" | sudo tee -a "$ini_file" > /dev/null
    ## echo "dgu.xmlrpc_username = CKAN_API" | sudo tee -a "$ini_file" > /dev/null
    ## echo "dgu.xmlrpc_password = XXX" | sudo tee -a "$ini_file" > /dev/null
    ## echo "dgu.xmlrpc_domain = 212.110.177.173" | sudo tee -a "$ini_file" > /dev/null
    ## echo "ckan.enable_call_timing = false" | sudo tee -a "$ini_file" > /dev/null
    
}

restore_database () {
    # Restores the database from a pg_dump file located at /tmp/dgu_live.pg_dump
    #
    # Requires 1 argument: the ckan instance name
    
    if [ $# -ne 1 ]
    then
        echo "resore_database() expects 1 argument: instance"
        exit 1
    fi

    dump_file=/home/ubuntu/dgu_live.pg_dump
    if [ ! -e $dump_file ]
    then
        echo "Can't restore database, dumpfile does not exist: $dump_file"
        exit 1
    fi

    instance=$1
    user="ckan$instance"
    ini_file="/etc/ckan/$instance/$instance.ini"

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
    old_shmmax=`cat /proc/sys/kernel/shmmax`
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

    # sourced from the dgu installation script
    run_database_migrations $instance "/home/ubuntu/users.csv"

}

create_test_admin_user () {
    echo "Creating admin user"
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan user add test_admin password=password --config=/etc/ckan/$instance/$instance.ini
    sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan sysadmin add test_admin --config=/etc/ckan/$instance/$instance.ini
    echo "Finished creating admin user"
}

run_database_migrations () {
    # usually 'overidden' by sourcing the buildbot/install_dgu_instance.sh script
    echo "No migration steps taken."
}

post_install () {
    # usually 'overidden' by sourcing the buildbot/install_dgu_instance.sh script
    echo "No post-installation steps taken."
}

restart_apache () {
    sudo /etc/init.d/apache2 restart
}

install_ckan $REPO $INSTANCE $DOMAIN
install_dgu $INSTANCE $BRANCH
restore_database $INSTANCE
configure_ini_file $INSTANCE $DOMAIN
create_test_admin_user $INSTANCE

# source the particular checkout's dependency post-installation function, post_install()
source "/var/lib/ckan/$INSTANCE/pyenv/src/ckanext-dgu/buildbot/install_dgu_instance.sh"
post_install $INSTANCE

restart_apache

echo "Rebuilding the index in the background..."
nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckan search-index rebuild --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/solr_output.log &
echo "Started the indexer"
echo "Starting the harvester import in the background..."
nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckanext-harvest harvester import --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/harvester_output.log &
echo "Started the import"

echo "Starting the qa update in the background..."
nohup sudo -u "$user" "/var/lib/ckan/$instance/pyenv/bin/paster" --plugin=ckanext-qa qa update --config=/etc/ckan/$instance/$instance.ini &> /home/ubuntu/qa_output.log &
echo "Started the update"
