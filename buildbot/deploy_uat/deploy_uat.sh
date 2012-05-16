#!/bin/bash

CKAN_VERSION=ckan-dgu1
INSTANCE=dgu-dev

# Pull in shared functions.
source install_dgu_instance.sh

update_src_repos () {
    # Upgrades the source installations

    

}

update_configs () {
    # Update config files
}

refresh_database () {
    # Tears down database, and re-runs migration scripts on it.
}

restart_daemons () {
    # Restart solr, celeryd etc.
}

update_ckan $REPO
