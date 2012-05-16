#!/bin/bash

#############################################################
# Fresh deployment on a new VM
#############################################################

if [ $# -ne 5 ]
then
    echo "Usage: `basename $0` repo-name ckan-instance-name domain dgu-branch xmlrpc-password"
    echo "\teg: `basename $0` ckan-1.5.1 std releasetest.ckan.org master super-secret-pass"
    exit 1
fi

REPO=$1
INSTANCE=$2
DOMAIN=$3
BRANCH=$4
XMLRPC_PASSWORD=$5

source ./common_functions.sh

install_ckan $REPO $INSTANCE $DOMAIN
install_dgu $INSTANCE $BRANCH
flush_database $INSTANCE "/home/ubuntu/deployment/dgu_live.pg_dump"
configure $INSTANCE $DOMAIN $XMLRPC_PASSWORD
create_test_admin_user $INSTANCE

restart_apache

rebuild_search_index $INSTANCE
start_harvest_import_daemon $INSTANCE
start_qa_daemon $INSTANCE

