'''
Datasets with duplicate GUIDs
https://github.com/datagovuk/ckanext-dgu/issues/263

Usage:

    python ckanext/dgu/bin/duplicates_from_harvest.py $CKAN_INI
'''

import sys
import common
from sqlalchemy import func

config_ini = sys.argv[1]
common.load_config(config_ini)
common.register_translator()

from ckan import model

extras = model.Session.query(model.PackageExtra.value, func.count(model.PackageExtra.value))\
    .filter_by(key='guid')\
    .filter_by(state='active')\
    .group_by(model.PackageExtra.value)\
    .having(func.count(model.PackageExtra.value) > 1)\
    .all()

count = 0
for guid, count_ in extras:
    datasets = model.Session.query(model.Package)\
        .filter_by(state='active')\
        .join(model.PackageExtra)\
        .filter_by(key='guid')\
        .filter_by(value=guid)\
        .filter_by(state='active')\
        .all()
    if len(datasets) > 1:
        count += 1
        print 'GUID: ', guid
        print '  %s datasets' % len(datasets)
        print '  ' + ' '.join(d.name for d in datasets)
        orgs = [d.get_organization() for d in datasets]
        print '  Org: ', ' '.join(set(org.name for org in orgs))

print 'Total: ', count
import pdb; pdb.set_trace()
