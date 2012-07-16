#!/bin/bash

#############################################################
# Fresh installation of dgu (without Drupal)
#############################################################

if [ $# -ne 4 ]
then
    echo "Usage: `basename $0` apt-repo-name ckan-instance-name domain dgu-branch"
    echo "\teg: `basename $0` ckan-dgu1 std releasetest.ckan.org master"
    exit 1
fi

REPO=$1
INSTANCE=$2
DOMAIN=$3
BRANCH=$4

DB_DUMP_FILE="../../dgu_live.pg_dump"
USERS_FILE="../../users.csv"
PUBLISHER_CONTACTS_FILE="../../dgu_pub_contacts.csv"
SECRETS_FILE="../../secrets.sh"

if [ ! -f $DB_DUMP_FILE ]
then
    echo "Missing database dump file: $DB_DUMP_FILE"
    exit 1
fi

if [ ! -f $USERS_FILE ]
then
    echo "Missing users file: $USERS_FILE"
    exit 1
fi

if [ ! -f $PUBLISHER_CONTACTS_FILE ]
then
    echo "Missing publisher contacts file: $PUBLISHER_CONTACTS_FILE"
    exit 1
fi

if [ ! -f $SECRETS_FILE ]
then
    echo "Missing secrets file: $SECRETS_FILE"
    exit 1
fi

source ./common_functions.sh

# Import secrets: $XMLRPC_PASSWORD and $OS_TILES_API_KEY
source $SECRETS_FILE

pause Installing CKAN
install_ckan $REPO

pause Creating CKAN instance
ckan-create-instance $INSTANCE $DOMAIN yes

pause Installing ckanext-dgu
install_dgu $INSTANCE $BRANCH

pause Loading database
clean_and_load_database $INSTANCE $DB_DUMP_FILE $USERS_FILE

pause Configuring CKAN
configure $INSTANCE $DOMAIN $XMLRPC_PASSWORD $OS_TILES_API_KEY

#create_test_admin_user $INSTANCE

pause Restarting apache
restart_apache

pause Rebuilding search index
rebuild_search_index $INSTANCE

pause Starting Harvest daemon
start_harvest_import_daemon $INSTANCE

pause Starting QA daemon
start_qa_daemon $INSTANCE

