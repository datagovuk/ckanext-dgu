'''
Checks the URLs of broken resource links to see if NationalArchives has
a copy we can use instead.
'''

import csv
import os
import json
import logging
import sys
import re

from paste.registry import Registry

import ckanext.dgu.bin.common as common
import time

from running_stats import Stats

global_log = logging.getLogger(__name__)

stats = Stats()

DATES = {
    1:   ["jan", "january"],
    2:   ["feb", "february"],
    3:   ["mar", "march"],
    4:   ["apr", "april"],
    5:   ["may"],
    6:   ["jun", "june"],
    7:   ["jul", "july"],
    8:   ["aug", "august"],
    9:   ["sep", 'sept', "september"],
    10: ["oct", "october"],
    11: ["nov", "november"],
    12: ["dec", "december"],
}

YEAR_RE = re.compile('^(\d{4})$')

def determine_date(title):
    year = 2000
    month = 1

    for p in title.split():
        for k, v in DATES.iteritems():
            if p.lower() in v:
                month = k
                continue
        m = YEAR_RE.match(p)
        if m:
            year = m.groups(0)[0]
    return "{0}/{1}".format(month, year)

def command(dataset_name, config_ini, commit=False):
    ckan = common.get_ckanapi(config_ini)
    package = ckan.action.package_show(id=dataset_name)

    timeseries_resources = [r for r in package.get('resources', []) if r.get('date')]

    # These shouldn't really be in the package, they're normally merged by the
    # schema - they don't appear in a call to /api/action/package_show. Why do they
    # keep turning up here.
    if 'timeseries_resources' in package:
        del package['timeseries_resources']
    if 'individual_resources' in package:
        del package['individual_resources']
    if 'additional_resources' in package:
        del package['additional_resources']

    if timeseries_resources:
        # We want to convert the other non-timeseries resources to timeseries
        updated = False
        resources = package.get('resources', [])
        for resource in resources:
            if resource['resource_type'] == 'documentation' or resource.get('date'):
                stats.add("Ignored Resource", resource['id'])
                continue

            updated = True
            resource['date'] = determine_date(resource['description'])
            stats.add("Resource updated", resource['id'])

        if updated:
            package['resources'] = resources

    if commit and updated:
        ckan.action.package_update(**package)
        print '*' * 60
        print "Dataset updated!"
    elif not updated:
        print '*' * 60
        print "Dataset was not updated"
    else:
        print '*' * 60
        print "DON'T PANIC, this was a dry run, nothing was committed"

    print ''
    print '*' * 60, 'Deletion Report'
    print stats.report(order_by_title=True)


def usage():
    print """
        Repairs resources in a dataset if some end up being timeseries and some individual.

        python ckanext/dgu/bin/repair_dataset.py <DATASET_NAME> <CONFIG_FILE or URL>
    """

if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()
        sys.exit(0)

    command(sys.argv[1], sys.argv[2], commit=len(sys.argv)==4 and sys.argv[3] == 'commit')
