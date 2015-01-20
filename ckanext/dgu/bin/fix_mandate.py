'''
Fix the mandate to be a JSON list

e.g.

http://example.com/ -> ['http://example.com']
'''

import common
import json
from optparse import OptionParser
from ckan import model

from running_stats import StatsList

stats = StatsList()


class FixMandate(object):
    @classmethod
    def command(cls, config_ini, write):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'script-fix_mandate.py'

        for package in model.Session.query(model.Package)\
                .filter(model.Package.state=='active'):
            if 'mandate' in package.extras:

                mandate = package.extras.get('mandate')

                if mandate:
                    print stats.add('Fixing (with value)', package.name)
                    package.extras['mandate'] = json.dumps([mandate])
                else:
                    print stats.add('Fixing (without value)', package.name)
                    package.extras['mandate'] = json.dumps([])
            else:
                stats.add('No mandate field', package.name)

        print stats.report()

        if write:
            print 'Writing'
            model.Session.commit()

usage = __doc__ + '''
Usage:
    python fix_mandate.py <CKAN config ini filepath> [--write]'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes to the datasets")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    FixMandate.command(config_ini, options.write)
