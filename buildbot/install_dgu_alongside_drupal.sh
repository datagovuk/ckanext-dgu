#!/bin/bash

#############################################################
# Configures an existing install of CKAN-DGU to sit next to
# Drupal
#############################################################

if [ $# -ne 4 ]
then
    echo "Usage: `basename $0` repo-name ckan-instance-name domain dgu-branch"
    echo "\teg: `basename $0` ckan-dgu1 std releasetest.ckan.org master"
    exit 1
fi

INSTANCE=$2
DOMAIN=$3

bash ./install_dgu.sh $1 $2 $3 $4

source ./common_functions.sh

install_joint_drupal_apache_config $INSTANCE $DOMAIN
