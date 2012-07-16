#!/bin/bash

#############################################################
# Update an existing dgu installation
#############################################################

if [ $# -ne 4 ]
then
    echo "Usage: `basename $0` repo-name ckan-instance-name domain dgu-branch"
    echo "\teg: `basename $0` ckan-dgu1 std releasetest.ckan.org master"
    exit 1
fi

REPO=$1
INSTANCE=$2
DOMAIN=$3
BRANCH=$4

DB_DUMP_FILE="../../dgu_live.pg_dump"
USERS_FILE="../../users.csv"
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

if [ ! -f $SECRETS_FILE ]
then
    echo "Missing secrets file: $SECRETS_FILE"
    exit 1
fi

source ./common_functions.sh

# Import secrets: $XMLRPC_PASSWORD and $OS_TILES_API_KEY
source $SECRETS_FILE

update_ckan $REPO
install_dgu $INSTANCE $BRANCH
clean_and_load_database $INSTANCE $DB_DUMP_FILE $USERS_FILE
configure $INSTANCE $DOMAIN $XMLRPC_PASSWORD $OS_TILES_API_KEY
## create_test_admin_user $INSTANCE

restart_apache

rebuild_search_index $INSTANCE
start_harvest_import_daemon $INSTANCE
start_qa_daemon $INSTANCE


