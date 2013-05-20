import os
import sys
import logging
import csv

from common import load_config, register_translator

USAGE = '''Shows all the email addresses for editors/admins of publishers
in PCTs.
Usage: python %s [config.ini]
''' % sys.argv[0]
if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h'):
    err = 'Error: Please specify config file.'
    print USAGE, err
    logging.error('%s\n%s' % (USAGE, err))
    sys.exit(1)
config_file = sys.argv[1]
config_ini_filepath = os.path.abspath(config_file)

# Load config to get access to the CKAN model
load_config(config_ini_filepath)
register_translator()
logging.config.fileConfig(config_ini_filepath)
log = logging.getLogger(os.path.basename(__file__))

# import CKAN here, rather than earlier, else their logging wont work
from ckan import model
from ckanext.dgu.lib import publisher as publisher_lib
from ckanext.dgu.drupalclient import DrupalClient, DrupalRequestError
from pylons import config
from running_stats import StatsList

# Drupal API
drupal = DrupalClient({'xmlrpc_domain': 'data.gov.uk',
                       'xmlrpc_username': config.get('dgu.xmlrpc_username'),
                       'xmlrpc_password': config.get('dgu.xmlrpc_password')})

user_emails = {} # name:email
def get_email_for_user(user):
    if user.name not in user_emails:
        if 'user_d' in user.name:
            user_drupal_id = user.name.replace('user_d', '')
            try:
                user_properties = drupal.get_user_properties(user_drupal_id)
            except DrupalRequestError, e:
                user_emails[user.name] = user.email
            else:
                user_emails[user.name] = user_properties['mail']
        else:
            # not a drupal user
            user_emails[user.name] = user.email
    return user_emails[user.name]

# NHS publishers
nhs = model.Group.by_name('national-health-service')
assert nhs
pub_stats = StatsList()
pct_rows = []
non_pct_rows = []
for pub in publisher_lib.go_down_tree(nhs):
    # Filter to PCTs
    title = pub.title
    not_pct = ('NHS Choices', 'NHS Connecting for Health', 'NHS Connecting for Health and NHS Business Services Authority')
    is_pct = ('Care Trust' in title or 'PCT' in title or title.startswith('NHS ') or 'Care Tust' in title) \
              and title not in not_pct and 'Foundation' not in title
    # Get the admins & editors
    admins = pub.members_of_type(model.User, 'admin').all()
    editors = pub.members_of_type(model.User, 'editor').all()
    # Get their email addresses
    users_with_email = []
    users_without_email = []
    warnings = None
    for user in admins:
        if get_email_for_user(user):
            users_with_email.append(user)
        else:
            users_without_email.append(user)
    if not users_with_email:
        if admins:
            warning = 'There is an admin(s) but not email addresses for them. '
        else:
            warning = 'There are no admins. '
    for user in editors:
        if get_email_for_user(user):
            users_with_email.append(user)
        else:
            users_without_email.append(user)
    if not users_with_email:
        if editors:
            warning += 'There is an editor(s) but not email addresses for them.'
        else:
            warning += 'There are no editors.'
    else:
        warning = None
    emails = ', '.join(['%s <%s>' % (user.fullname, get_email_for_user(user)) \
                        for user in users_with_email])
    names_without_email = ', '.join([user.fullname or user.name\
                                     for user in users_without_email])
    if warning:
        print pub_stats.add('%s without emails: %s' % ('PCT' if is_pct else 'Trust', warning), pub.title)
    else:
        print pub_stats.add('%s with emails' % 'PCT' if is_pct else 'Trust', pub.title)
    row = ('PCT' if is_pct else '',
           pub.title, pub.name, emails, warning)
    if is_pct:
        pct_rows.append(row)
    else:
        non_pct_rows.append(row)

print pub_stats.report()

filename = 'nhs_emails.csv'
with open(filename, 'wb') as csvfile:
    csv_writer = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow(['PCT?', 'Publisher title', 'Publisher name', 'Emails', 'Warnings'])
    for row in pct_rows + non_pct_rows:
        csv_writer.writerow(row)
print filename
