'''
Resets package contact details for packages which have the same contact details as their group (due to UI bug)
'''

import os
import sys
from sqlalchemy import engine_from_config
from pylons import config
import common
from optparse import OptionParser
from ckan import model

from running_stats import StatsList

stats = StatsList()

def package_is_effected(package, group):
    if not (package.extras.get('contact-name') or
            package.extras.get('contact-email') or
            package.extras.get('contact-phone') or
            package.extras.get('foi-name') or
            package.extras.get('foi-email') or
            package.extras.get('foi-web') or
            package.extras.get('foi-phone')):
        stats.add('No contact details', package.name)
        return False
    return ((package.extras.get('contact-name') == group.extras.get('contact-name')) and
            (package.extras.get('contact-email') == group.extras.get('contact-email')) and
            (package.extras.get('contact-phone') == group.extras.get('contact-phone')) and
            (package.extras.get('foi-name') == group.extras.get('foi-name')) and
            (package.extras.get('foi-email') == group.extras.get('foi-email')) and
            (package.extras.get('foi-web') == group.extras.get('foi-name')) and
            (package.extras.get('foi-phone') == group.extras.get('foi-phone')))

class FixContactDetails(object):
    @classmethod
    def command(cls, config_ini, write):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'fix_contact_details.py'

        for package in model.Session.query(model.Package).filter_by(state='active'):
            group = package.get_organization()
            if not group:
                stats.add('was not in a group', package.name)
                continue

            if package.extras.get('contact-name') == group.extras.get('contact-name'):
                if package_is_effected(package, group):
                    if write:
                        package.extras['contact-name'] = ''
                        package.extras['contact-email'] = ''
                        package.extras['contact-phone'] = ''
                        package.extras['foi-name'] = ''
                        package.extras['foi-email'] = ''
                        package.extras['foi-web'] = ''
                        package.extras['foi-phone'] = ''
                    stats.add('resetting', 'Resetting package %s' % package.name)

        print stats.report()
        if write:
            model.Session.commit()


def usage():
    print """
Resets package contact details for packages which have the same contact details as their group (due to UI bug)
Usage:

    python fix_contact_details.py <CKAN config ini filepath>
    """

if __name__ == '__main__':
    parser = OptionParser(usage='')
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes to the datasets")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        usage()
        sys.exit(0)
    config_ini = args[0]
    FixContactDetails.command(config_ini, options.write)
