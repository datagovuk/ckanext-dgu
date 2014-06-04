'''Tool for dealing with public body data and reconciliation with the likes of
GDS, data.gov.uk and opennames.org.
'''

# Requires:
# git clone git@github.com:pudo/pynomenklatura.git
# pip install -e pynomenklatura

# Cheat sheet for command-line nomenklatura:
# import nomenklatura
# opennames = nomenklatura.Dataset('public-bodies-uk')
# entity = opennames.entity_by_name('Dept Education')
# entity.canonical = opennames.entity_by_name('Department for Education').id
# entity.update()
# opennames.create_entity('Department of Business', attributes={}, reviewed=False)

import json
import sys
import nomenklatura
from nomenklatura import NoMatch
from running_stats import Stats
import requests

def gds_reconcile():
    stats = Stats()
    attribute_conflicts = []
    gds_page_number = 0
    while True:
        gds_page_number += 1
        gds_page = requests.get('https://www.gov.uk/api/organisations?page=%d' % gds_page_number)
        orgs = json.loads(gds_page.content)['results']
        if not orgs:
            break
        for org in orgs:
            status = 'closed' if org['details']['govuk_status'] == 'closed' else 'active'
            attributes = {'govuk-id': org['id'],
                        'govuk-url': org['web_url'],
                        'category': org['format'], # e.g. "Ministerial department"
                        }
            merge_attributes = {
                        'abbreviation': org['details']['abbreviation'],
                        'status': status # "closed"/"active"
                        }
            _merge_org(org['title'], attributes, merge_attributes, stats,
                       attribute_conflicts)
    print stats
    _print_attribute_conflicts(attribute_conflicts)

def dgu_reconcile():
    stats = Stats()
    attribute_conflicts = []
    org_names_request = requests.get('http://data.gov.uk/api/action/organization_list')
    # NB Not using all_fields as it doesn't include extras, like category
    org_names = json.loads(org_names_request.content)['result']
    for org_name in org_names:
        org_request = requests.get('http://data.gov.uk/api/action/organization_show?id=%s' % org_name)
        org = json.loads(org_request.content)['result']
        # convert the extras into a dict
        org['extras'] = dict((extra['key'], extra['value']) for extra in org['extras'])
        attributes = {
                    'dgu-name': org['name'],
                    'dgu-uri': 'http://data.gov.uk/publisher/%s' % org['name'],
                    }
        merge_attributes = {
                    'abbreviation': org['extras'].get('abbreviation'),
                    'category': 'Local authority' if org['extras'].get('category') == 'local-council' else None,
                    }
        _merge_org(org['title'], attributes, merge_attributes, stats,
                   attribute_conflicts)
    print stats
    _print_attribute_conflicts(attribute_conflicts)


def _merge_org(org_title, attributes, merge_attributes, stats, attribute_conflicts):
    '''
    attributes are set on opennames if there is a value specified (will overwrite on opennames).
    merge_attributes are set on opennames if there is a value specified and no value exists on opennames. If there a different value exists on opennames already then this is noted in attribute_conflicts.
    '''
    opennames = nomenklatura.Dataset('public-bodies-uk')

    # remove blank attributes
    attributes = dict((k, v) for k, v in attributes.items() if v)
    merge_attributes = dict((k, v) for k, v in merge_attributes.items() if v)
    try:
        entity = opennames.entity_by_name(org_title)
    except NoMatch:
        attributes.update(dict((k, v) for k, v in merge_attributes.items() if v))
        opennames.create_entity(
                org_title,
                attributes=attributes,
                reviewed=False)
        print stats.add('created', org_title)
    else:
        # It exists, but might need its attributes adding/updating
        if entity.is_alias:
            entity = entity.canonical
        needs_update = False
        for key, value in attributes.items():
            if key not in entity.attributes or \
                    entity.attributes[key] != value:
                needs_update = True
                entity.attributes[key] = value
        for key, value in merge_attributes.items():
            if key not in entity.attributes:
                needs_update = True
                entity.attributes[key] = value
            elif entity.attributes[key] and \
                    entity.attributes[key].lower() != value.lower():
                attribute_conflicts.append((org_title, key, entity.attributes[key], value))
                print 'ATTRIBUTE CONFLICT', attribute_conflicts[-1]

        if needs_update:
            entity.update()
            print stats.add('updated', org_title)
        else:
            print stats.add('unchanged', org_title)

def _print_attribute_conflicts(attribute_conflicts):
    if attribute_conflicts:
        print 'Attribute conflicts (unresolved):'
        for conflict in attribute_conflicts:
            print '* %r' % repr(conflict)

if __name__ == '__main__':
    usage = __doc__ + """
usage:

python public_bodies.py gds-reconcile organisations.json
  Gets GDS/gov.uk's list of organizations and loads into opennames.org for
  reconciliation.

python public_bodies.py dgu-reconcile organisations.json
  Gets data.gov.uk's list of organizations and loads into opennames.org for
  reconciliation.
"""
    if len(sys.argv) < 2 or sys.argv in ('-h', '--help'):
        print usage
        sys.exit(1)
    command = sys.argv[1]
    args = sys.argv[2:]
    if command == 'gds-reconcile':
        gds_reconcile()
    elif command == 'dgu-reconcile':
        dgu_reconcile()
    else:
        sys.stderr.write('Command not recognized: %s' % command)
        sys.exit(1)
