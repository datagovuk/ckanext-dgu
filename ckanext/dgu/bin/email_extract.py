'''
Prints email addresses for editors/admins from organizations.
'''
import argparse

import requests_cache
import ckanapi

from ckanext.dgu.bin import common

args = None

one_day = 60 * 60 * 24
one_month = one_day * 30
requests_cache.install_cache('.email_extract_cache', expire_after=one_month)
ckan = ckanapi.RemoteCKAN('https://data.gov.uk', get_only=True)
ckan_uncached = ckanapi.RemoteCKAN('https://data.gov.uk', get_only=False)
ckan_admin = None


user_cache = {}
def get_user(id_):

    if id_ not in user_cache:
        global ckan_admin
        if ckan_admin is None:
            ckan_admin = common.get_ckanapi('https://data.gov.uk',
                                            get_only=True)
        try:
            user = ckan_admin.action.user_show(id=id_)
        except ckanapi.NotFound:
            user = None
        user_cache[id_] = user
    return user_cache[id_]


def get_extra(org, key, default=None):
    for extra in org['extras']:
        if extra['key'] == key:
            return extra['value']
    return default


def print_user(user, custom_info=''):
    print '  %s <%s> %s' % (user['fullname'], user['email'], custom_info)


def get_emails():
    if args.organization:
        # single organization
        org_name = common.name_stripped_of_url(args.organization)
        org_name, result_emails = get_emails_for_organization(org_name)
        result_orgs = [org_name]
    else:
        # check through all the organizations
        org_names = ckan.action.organization_list()
        result_orgs = []
        result_emails = []
        for org_name in org_names:
            # org filtered using cached organizations
            print 'Getting: %s' % org_name
            org = ckan.action.organization_show(
                id=org_name,
                include_users=False,
                include_datasets=False)
            if get_extra(org, 'closed', '').lower() == 'true':
                continue
            if args.departments:
                category = get_extra(org, 'category')
                if category not in ('ministerial-department',
                                    'non-ministerial-department'):
                    continue
                if org['groups'] != []:
                    if 'northern-ireland-executive' in str(org['groups']):
                        # exclude NI ones
                        continue
                    if org_name not in (
                            'crown-prosecution-service',
                            'united-kingdom-export-finance',
                            'serious-fraud-office',
                            'ordnance-survey',
                            'office-of-rail-and-road',
                            'office-of-qualifications-and-examinations-regulation',
                            'office-for-standards-in-education-childrens-services-and-skills',
                            'land-registry',
                            'government-actuarys-department',
                            'forestry-commission',
                            'government-legal-department',
                            'the-national-archives',
                            'national-crime-agency',
                            ):
                        print 'WARN: Should this be a central government ' \
                            ' department - it is not at top level! %s' \
                            % org['name']

            org_name, emails = get_emails_for_organization(org_name)
            result_orgs.append(org_name)
            result_emails.extend(emails)

    print '\nSummary:'
    print '%s organizations' % len(result_orgs)
    print '%s emails:' % len(result_emails)
    result_emails = dedupe_list(result_emails)
    print '%s emails (deduped):' % len(result_emails)
    print ', '.join(result_emails)


def get_emails_for_organization(org_name):
    # uncached org
    org = ckan_uncached.action.organization_show(
        id=org_name,
        include_users=True,
        include_datasets=False)
    print org['title']
    emails = []
    for user_summary in org['users']:
        user = get_user(user_summary['name'])
        print_user(user, user_summary['capacity'])
        emails.append('%s <%s>' % (user['fullname'], user['email']))
    return (org['name'], emails)


def dedupe_list(list_):
    l = list_
    return reduce(lambda r, v: v in r[1] and r or
                  (r[0].append(v) or r[1].add(v))
                  or r, l, ([], set()))[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--departments', action='store_true',
                        help='Filter for central government departments')
    parser.add_argument('-o', '--organization',
                        help='Filter for a particular organization')
    args = parser.parse_args()
    if not (args.departments or args.organization):
        parser.error(
            'You must filter by something - am not going to dump all users')
    get_emails()
