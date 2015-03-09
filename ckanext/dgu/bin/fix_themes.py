'''
Fix the themes to be the long form

e.g.

Crime -> Crime & Justice
'''

import common
import json
from optparse import OptionParser
from ckan import model

from running_stats import StatsList

stats = StatsList()

THEMES = {
    u"Health": u"Health",
    u"Environment": u"Environment",
    u"Education": u"Education",
    u"Crime": u"Crime & Justice",
    u"Government": u"Government",
    u"Defence": u"Defence",
    u"Economy": u"Business & Economy",
    u"Transport": u"Transport",
    u"Spending": u"Government Spending",
    u"Society": u"Society",
    u"Mapping": u"Mapping",
    u"Towns": u"Towns & Cities",
}

class FixThemes(object):
    @classmethod
    def command(cls, config_ini, options):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'script-fix_themes.py'

        datasets = common.get_datasets(state='active',
                                       dataset_name=options.dataset)
        for package in datasets:
            if 'theme-primary' in package.extras:
                primary = package.extras.get('theme-primary')
                new_primary = THEMES.get(primary, primary)
                if new_primary != primary:
                    stats.add('Fixing primary theme', package.name)
                    package.extras['theme-primary'] = new_primary
                else:
                    stats.add('Not fixing primary theme', package.name)
            else:
                stats.add('No primary theme', package.name)

            if 'theme-secondary' in package.extras:
                secondary = package.extras.get('theme-secondary')
                try:
                    secondary = json.loads(secondary)

                    if isinstance(secondary, list):
                        new_secondary = [THEMES.get(x, x) for x in secondary]
                    elif isinstance(secondary, basestring):
                        new_secondary = THEMES.get(secondary, secondary)
                    else:
                        stats.add('Problem JSON', package.name)
                        del package.extras['theme-secondary']
                        continue
                except ValueError:
                    stats.add('Error decoding JSON', package.name)
                    if secondary.startswith('{') and secondary.endswith('}'):
                        new_secondary = secondary[1:-1] # '{Crime}' -> 'Crime'
                    else:
                        del package.extras['theme-secondary']
                        continue

                if new_secondary != secondary:
                    stats.add('Fixing secondary theme', package.name)
                    package.extras['theme-secondary'] = json.dumps(new_secondary)
                else:
                    stats.add('Not fixing secondary theme', package.name)
            else:
                stats.add('No secondary theme', package.name)

        print stats.report()

        if options.write:
            print 'Writing'
            model.Session.commit()

usage = __doc__ + '''
Usage:
    python fix_themes.py <ckan.ini> [--write]'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes to the datasets")
    parser.add_option('-d', '--dataset', dest='dataset')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    FixThemes.command(config_ini, options)
