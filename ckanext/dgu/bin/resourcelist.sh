#!/bin/bash

###############################################################################
# Helper script that will ask a remote server, via the API, what URLs it has
# for a specific publisher.
#
# This tool requires jq to be installed (http://stedolan.github.io/jq/) which
# can be installed with 'brew install jq'
###############################################################################
die () {
    echo >&2 "$@"
    echo "
        Usage:

        ./resourcelist.sh environment-agency data.gov.uk

        'jq' is required from http://stedolan.github.io/jq/ but can be installed
        with brew 'brew install jq'
    "
    exit 1
}

type jq >/dev/null 2>&1 || { echo >&2 "'jq' is required but it's not installed.  Aborting."; exit 1; }

[ "$#" -eq 2 ] || die "2 arguments required, $# provided. Specify publisher short-name and server"

PUBLISHER="$1"
SERVER="$2"
PIDFILE="$PUBLISHER-packages.txt"
RESFILE="$PUBLISHER-urls.txt"


# Fetch a list of package IDs
echo "Fetching package IDs for $PUBLISHER from $SERVER"
curl -s http://$SERVER/api/3/action/organization_show?id=$PUBLISHER | jq -c -M -r '.result.packages[].id' > $PIDFILE

# Let the user know how many packages we've got
PACKAGE_COUNT=`awk '{x++}END{ print x}' $PIDFILE`
echo "Processing $PACKAGE_COUNT packages"

COUNTER=0
while read i; do
    curl -s http://$SERVER/api/3/action/package_show?id=$i | jq -c -M -r '.result.resources[].url' >> $RESFILE
    sleep 1s
    TOTAL=`awk '{x++}END{ print x}' $RESFILE`
    let COUNTER+=1
    echo -n -e "Processed $i: $COUNTER/$PACKAGE_COUNT Total resources: $TOTAL\r"
done < $PIDFILE

# Strip blank lines
sed -i -e '/^$/d' $RESFILE

echo -e "\n...Done. Output is in $RESFILE"
