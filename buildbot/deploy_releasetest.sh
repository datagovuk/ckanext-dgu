#!/bin/bash

#############################################################
# Fresh deployment on a new VM
#############################################################

if [ $# -ne 4 ]
then
    echo "Usage: `basename $0` repo-name ckan-instance-name domain dgu-branch xmlrpc-password"
    echo "\teg: `basename $0` ckan-1.5.1 std releasetest.ckan.org master super-secret-pass"
    exit 1
fi

REPO=$1
INSTANCE=$2
DOMAIN=$3
BRANCH=$4

source ./common_functions.sh

# Import secrets: $XMLRPC_PASSWORD and $OS_TILES_API_KEY
source /home/ubuntu/deployment/secrets.sh

install_ckan $REPO 
ckan-create-instance $INSTANCE $DOMAIN yes
install_dgu $INSTANCE $BRANCH
clean_and_load_database $INSTANCE "/home/ubuntu/deployment/dgu_live.pg_dump" "/home/ubuntu/deployment/users.csv"
configure $INSTANCE $DOMAIN $XMLRPC_PASSWORD $OS_TILES_API_KEY
create_test_admin_user $INSTANCE

restart_apache

rebuild_search_index $INSTANCE
start_harvest_import_daemon $INSTANCE
start_qa_daemon $INSTANCE

