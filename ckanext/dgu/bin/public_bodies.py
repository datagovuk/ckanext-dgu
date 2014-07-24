'''Tool for dealing with public body data and reconciliation with the likes of
GDS, data.gov.uk and opennames.org.
'''

# Requires:
# git clone git@github.com:pudo/pynomenklatura.git
# pip install -e pynomenklatura

# Cheat sheet for command-line nomenklatura:
# import nomenklatura
# opennames = nomenklatura.Dataset('public-bodies-uk')
# entity = opennames.entity_by_name('Department for Education')
# entity.attributes
# entity.canonical = opennames.entity_by_name('Department for Education').id
# entity.update()
# opennames.create_entity('Department of Business', attributes={}, reviewed=False)

import json
import sys
import time

import nomenklatura
from nomenklatura import NoMatch
from running_stats import Stats
import requests

def gds_reconcile():
    stats = Stats()
    messages = Messages()
    gds_page_number = 0
    while True:
        gds_page_number += 1
        url = 'https://www.gov.uk/api/organisations?page=%d' % gds_page_number
        print url
        gds_page = requests.get(url)
        orgs = json.loads(gds_page.content)['results']
        if not orgs:
            break
        for org in orgs:
            status = 'closed' if org['details']['govuk_status'] == 'closed' else 'active'
            # TODO for closed departments, scrape gov.uk to find out the
            # replacement department. e.g.
            # https://www.gov.uk/api/organisations/department-of-constitutional-affairs
            attributes = {'govuk-id': org['id'],
                        'govuk-url': org['web_url'],
                        'category': org['format'], # e.g. "Ministerial department"
                        }
            merge_attributes = {
                        'abbreviation': org['details']['abbreviation'],
                        'status': status # "closed"/"active"
                        }
            _merge_org(org['title'], attributes, merge_attributes, stats,
                       messages)
    print stats
    _print_messages(messages)

def dgu_reconcile():
    from ckanext.dgu.forms import validators
    stats = Stats()
    messages = Messages()
    org_names_request = requests.get('http://data.gov.uk/api/action/organization_list')
    dgu_categories = dict(validators.categories)

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
        category = org['extras'].get('category')
        merge_attributes = {
                    'abbreviation': org['extras'].get('abbreviation'),
                    'category': dgu_categories[category] if category in dgu_categories else None,
                    }
        _merge_org(org['title'], attributes, merge_attributes, stats,
                   messages)
    print stats
    _print_messages(messages)

orgs_processed = {}  # name: properties

def _merge_org(org_title, attributes, merge_attributes, stats, messages):
    '''
    attributes are set on opennames if there is a value specified (will
    overwrite on opennames).  merge_attributes are set on opennames if there is
    a value specified and no value exists on opennames. If there a different
    value exists on opennames already then this is noted in
    messages.
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

        # Check we've not done this org before
        all_attributes = dict(attributes.items() + merge_attributes.items())
        base_entity = entity.canonical if entity.is_alias else entity
        if base_entity.name in orgs_processed:
            msg = 'DUPLICATE - ignored'
            if entity.is_alias:
                msg += ' (alias of "%s")' % entity.canonical.name
            else:
                aliases = [e.name for e in entity.aliases]
                if aliases:
                    msg += ' (has alias "%s")' % '", "'.join(aliases)
            diff = dicts_differences(all_attributes, orgs_processed[base_entity.name], ignore_keys=('govuk-id', 'govuk-url'))
            if not diff:
                print stats.add('Repeat org with identical attributes - '
                                'ignored', org_title)
                return
            msg += ' - differences: %s' % diff
            messages.append(Message(entity.name, msg))
            print stats.add('Repeat org with different attributes - '
                            'review', org_title)
            return
        orgs_processed[base_entity.name] = all_attributes

        entity = base_entity

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
                messages.append(AttributeConflict(org_title, key, entity.attributes[key], value))

        if needs_update:
            entity.update()
            print truncate(stats.add('updated', org_title), 78)
        else:
            print truncate(stats.add('unchanged', org_title), 78)


def dicts_differences(dict1, dict2, ignore_keys=None):
    differences = []
    dict1_only = set(dict1.keys()) - set(dict2.keys()) - set(ignore_keys)
    if dict1_only:
        differences.append('Only in 1st dict: %s' % dict1_only)
    dict2_only = set(dict2.keys()) - set(dict1.keys()) - set(ignore_keys)
    if dict2_only:
        differences.append('Only in 2nd dict: %s' % dict2_only)
    common_keys = (set(dict2.keys()) & set(dict1.keys())) - set(ignore_keys)
    for key in common_keys:
        if dict1[key] != dict2[key]:
            differences.append('%s = "%s" vs "%s"' % (key, dict1[key], dict2[key]))
    return '; '.join(differences)


def truncate(string, max_length, suffix='...'):
    if len(string) > max_length:
        string = string[:max_length-len(suffix)] + suffix
    return string


class Messages(list):
    def append(self, msg):
        super(Messages, self).append(msg)
        print msg


class Message(object):
    def __init__(self, organization_title, msg):
        self.organization_title = organization_title
        self.msg = msg

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s: %s' % (self.organization_title, self.msg)


class AttributeConflict(Message):
    def __init__(self, organization_title, attribute_key,
                 existing_value, potential_value):
        self.organization_title = organization_title
        self.attribute_key = attribute_key
        self.existing_value = existing_value
        self.potential_value = potential_value

    def __unicode__(self):
        return u'%s: ATTRIBUTE %s=%s suggestion=%s' % (self.organization_title,
                self.attribute_key, self.existing_value, self.potential_value)


def _print_messages(messages):
    if messages:
        print 'Messages:'
        for msg in sorted(messages, key=lambda m: type(m)):
            print '* %s' % msg


def opennames_update(org_name, attribute, value):
    opennames = nomenklatura.Dataset('public-bodies-uk')
    entity = opennames.entity_by_name(org_name)
    assert attribute in entity.attributes, \
        'Attribute "%s" not in entity: %r - it has: %r' % \
        (attribute, entity, entity.attributes)
    entity.attributes[attribute] = value
    print 'Writing %s=%s' % (attribute, value)
    entity.update()


def dgu_update(apikey):
    from ckanext.dgu.forms import validators
    import ckanapi
    dgu = ckanapi.RemoteCKAN('http://data.gov.uk',
                             user_agent=__file__,
                             apikey=apikey)
    dgu_categories = dict(validators.categories)
    dgu_categories_by_title = dict((title, id)
                                   for id, title in validators.categories)
    stats_category = Stats()
    stats_state = Stats()
    org_names_request = requests.get('http://data.gov.uk/api/action/organization_list')
    # NB Not using all_fields as it doesn't include extras, like category
    org_names = json.loads(org_names_request.content)['result']
    opennames = nomenklatura.Dataset('public-bodies-uk')
    for org_name in org_names:
        org_request = requests.get('http://data.gov.uk/api/action/organization_show?id=%s' % org_name)
        org = json.loads(org_request.content)['result']
        # convert the extras into a dict
        org['extras'] = dict((extra['key'], extra['value'])
                             for extra in org['extras'])
        try:
            entity = opennames.entity_by_name(org['title'])
        except NoMatch:
            # BTW it hasn't been added for review
            msg = 'Org not found in nomenklatura'
            print stats_category.add(msg, org_name)
            stats_state.add(msg, org_name)
            continue
        entity = entity.dereference()
        changed_org = dgu_update_category(org_name, org, entity, stats_category, dgu_categories, dgu_categories_by_title)
        if changed_org:
            # convert the extras back into a list of dicts
            org['extras'] = [{'key': key, 'value': value}
                             for key, value in org['extras'].items()]
            try:
                org = dgu.action.organization_update(**org)
            except ckanapi.errors.CKANAPIError, e:
                if '504 Gateway Time-out' in str(e):
                    print stats_category.add('Time-out writing', org_name)
                else:
                    raise

    stats_category.report_value_limit = 500
    print 'Category:\n', stats_category.report()
    print 'State:\n', stats_state.report()


def dgu_update_category(org_name, org, entity, stats, dgu_categories, dgu_categories_by_title):
    opennames_category = entity.attributes.get('category')
    opennames_category_id = dgu_categories_by_title.get(opennames_category)
    if opennames_category and not opennames_category_id:
        print stats.add('Opennames category not in DGU validators.py - will be ignored: "%s"' % opennames_category, org_name)
        return
    dgu_category_id = org.get('category')
    if dgu_category_id and dgu_category_id not in dgu_categories:
        # erase non-validating values
        dgu_category_id = None
    if opennames_category_id:
        if dgu_category_id:
            if opennames_category_id != dgu_category_id:
                print stats.add('Disagreement - review',
                        '%s: Opennames=%s DGU=%s' %
                        (org_name, opennames_category_id, dgu_category_id))
                return
            else:
                print stats.add('Agreement - ok',
                        '%s: %s' % (org_name, dgu_category_id))
                return
        else:
            print stats.add('Changed',
                    '%s: %s' % (org_name, opennames_category_id))
            org['category'] = opennames_category_id
            return True
    else:
        if dgu_category_id:
            print stats.add('Opennames has no value, but DGU has',
                        '%s: %s' % (org_name, dgu_category_id))
            return
        else:
            print stats.add('Opennames has no value, nor does DGU', org_name)
            return


def dgu_update_org(org_name, attribute, value, apikey):
    import ckanapi
    dgu = ckanapi.RemoteCKAN('http://data.gov.uk',
                             user_agent=__file__,
                             apikey=apikey)
    org = dgu.action.organization_show(id=org_name)
    if attribute in org:
        before = org[attribute]
        org[attribute] = value
        print 'Changing %s=%s->%s' % (attribute, before, value)
    else:
        for extra in org['extras']:
            if extra['key'] == attribute:
                before = extra['value']
                extra['value'] = value
                print 'Changing %s=%s->%s' % (attribute, before, value)
                break
        else:
            print 'Could not find attribute %s' % attribute
    org = dgu.action.organization_update(**org)
    from pprint import pprint
    pprint([e for e in org['extras'] if e['key'] == 'category'])


def opennames_swap_alias(org_name):
    # NB there are issues - see https://github.com/pudo/nomenklatura/issues/35
    # get all the entities
    opennames = nomenklatura.Dataset('public-bodies-uk')
    entity_to_make_canonical = opennames.entity_by_name(org_name)
    assert entity_to_make_canonical.is_alias
    entity_that_was_canonical = entity_to_make_canonical.canonical
    other_aliases = [e for e in entity_that_was_canonical.aliases
                     if e.id != entity_to_make_canonical.id]
    # swap the aliases
    entity_that_was_canonical.__data__['canonical'] = entity_to_make_canonical.__data__
    entity_to_make_canonical.__data__['canonical'] = None
    entity_to_make_canonical.attributes = entity_that_was_canonical.attributes
    entity_that_was_canonical.attributes = {}
    for entity in other_aliases:
        entity.__data__['canonical'] = entity_to_make_canonical.__data__
    # write
    for entity in [entity_that_was_canonical,
                   entity_to_make_canonical] + other_aliases:
        entity.update()


def _parse_setting(setting):
    if '=' not in setting:
        sys.stderr.write('Setting must have an equals sign. Got: %r' % setting)
        sys.exit(1)
    equal_index = setting.find('=')
    attribute = setting[:equal_index]
    value = setting[equal_index+1:]
    return attribute, value


if __name__ == '__main__':
    usage = __doc__ + """
usage:

python public_bodies.py gds-reconcile
  Gets GDS/gov.uk's list of organizations and loads into opennames.org for
  reconciliation.

python public_bodies.py dgu-reconcile
  Gets data.gov.uk's list of organizations and loads into opennames.org for
  reconciliation.

python public_bodies.py dgu-update
  Updates data.gov.uk's list of organization properties from those resolved in
  opennames.org.

python public_bodies.py dgu-update "organization-name" <attribute>="value"
  Updates a data.gov.uk organization's property.

python public_bodies.py opennames-update "Organization Name" <attribute>="value"
  Updates an opennames.org organization property.

python public_bodies.py opennames-swap-alias "Organization Name"
  Makes the given opennames.org alias into an entity, and its entity into an alias.
"""
    if len(sys.argv) < 2 or set(sys.argv) & set(('-h', '--help')):
        print usage
        sys.exit(1)
    command = sys.argv[1]
    args = sys.argv[2:]
    if command == 'gds-reconcile':
        gds_reconcile()
    elif command == 'dgu-reconcile':
        dgu_reconcile()
    elif command == 'dgu-update':
        if len(args) == 1:
            apikey = args[0]
            dgu_update(apikey)
        elif len(args) == 3:
            org_name, setting, apikey = args
            attribute, value = _parse_setting(setting)
            dgu_update_org(org_name, attribute, value, apikey)
        else:
            sys.stderr.write('Command must have 0 or 3 arguments, got %d' % len(args))
            sys.exit(1)
    elif command == 'opennames-update':
        if len(args) != 2:
            sys.stderr.write('Command must have 2 arguments, got %d' % len(args))
            sys.exit(1)
        org_name, setting = args
        attribute, value = _parse_setting(setting)
        opennames_update(org_name, attribute, value)
    elif command == 'opennames-swap-alias':
        if len(args) != 1:
            sys.stderr.write('Command must have 1 argument, got %d' % len(args))
            sys.exit(1)
        opennames_swap_alias(org_name=args[0])
    else:
        sys.stderr.write('Command not recognized: %s' % command)
        sys.exit(1)
