#!/bin/bash

#############################################################
# Upgrade an existing deployment
#############################################################

if [ $# -ne 6 ]
then
    echo "Usage: `basename $0` repo-name ckan-instance-name domain dgu-branch xmlrpc-password rebuild-database?"
    echo "\teg: `basename $0` ckan-1.5.1 std releasetest.ckan.org master super-secret-pass yes"
    exit 1
fi

REPO=$1
INSTANCE=$2
DOMAIN=$3
BRANCH=$4
XMLRPC_PASSWORD=$5
REBUILD_DATABASE=$6

source ./common_functions.sh

update_ckan $REPO
install_dgu $INSTANCE $BRANCH

if [[ $REBUILD_DATABASE == "yes" ]];
then
    clean_and_load_database $INSTANCE
    create_test_admin_user $INSTANCE
fi

configure $INSTANCE $DOMAIN $XMLRPC_PASSWORD

restart_apache

rebuild_search_index $INSTANCE
start_harvest_import_daemon $INSTANCE
start_qa_daemon $INSTANCE


