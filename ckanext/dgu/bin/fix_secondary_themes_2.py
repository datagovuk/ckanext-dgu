'''
Fix the multiple JSON encoding of the secondary theme extra

e.g.

"[\"Health\"]" -> ["Health"]
'''

import os
import sys
from sqlalchemy import engine_from_config
from pylons import config
import common
import ast
import json
from optparse import OptionParser
from ckan import model

from running_stats import StatsList

stats = StatsList()


class FixSecondaryTheme2(object):
    @classmethod
    def command(cls, config_ini, write):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'fix_secondary_theme.py'

        for package in model.Session.query(model.Package):
            if 'theme-secondary' in package.extras:
                stats.add('Testing', package.name)

                secondary_theme = package.extras.get('theme-secondary')

                while isinstance(secondary_theme, basestring):
                    try:
                        secondary_theme = json.loads(secondary_theme)
                    except ValueError:
                        if secondary_theme == 'None':
                            secondary_theme = []
                        else:
                            secondary_theme = secondary_theme.split(',')
                        break

                if json.dumps(secondary_theme) != package.extras.get('theme-secondary'):
                    stats.add('Fixing', package.name)
                    if secondary_theme == 'None' or secondary_theme == '':
                        package.extras['theme-secondary'] = json.dumps([])
                    else:
                        package.extras['theme-secondary'] = json.dumps(secondary_theme)

        if write:
            model.Session.commit()

        print stats.report()


def usage():
    print """
Fix the multiple JSON encoding of the secondary theme extra

Usage:

    python fix_secondary_theme_2.py <CKAN config ini filepath>
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
    FixSecondaryTheme2.command(config_ini, options.write)
