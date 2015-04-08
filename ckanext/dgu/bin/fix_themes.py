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

stats_primary = StatsList()
stats_secondary = StatsList()

THEME_MAP = {
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
THEMES = THEME_MAP.values()

class FixThemes(object):
    @classmethod
    def command(cls, config_ini, options):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'script-fix_themes.py'

        datasets = common.get_datasets(state='active',
                                       dataset_name=options.dataset,
                                       organization_ref=options.organization)
        for package in datasets:
            if 'theme-primary' in package.extras:
                primary = package.extras.get('theme-primary')
                if not primary:
                    stats_primary.add('Blank', package.name)
                elif primary in THEMES:
                    stats_primary.add('Ok', package.name)
                else:
                    new_primary = THEME_MAP.get(primary)
                    if new_primary is None:
                        print stats_primary.add('Unknown theme %s' % primary, package.name)
                    else:
                        assert(new_primary != primary)
                        print stats_primary.add('Changed to long form', package.name)
                        package.extras['theme-primary'] = new_primary
            else:
                stats_primary.add('No theme', package.name)

            if 'theme-secondary' in package.extras:
                secondary = package.extras.get('theme-secondary')
                try:
                    secondary = json.loads(secondary)

                    if isinstance(secondary, list):
                        new_secondary = [THEME_MAP.get(x, x) for x in secondary]
                    elif isinstance(secondary, basestring):
                        new_secondary = THEME_MAP.get(secondary, secondary)
                    else:
                        stats_secondary.add('Problem JSON', package.name)
                        del package.extras['theme-secondary']
                        continue
                except ValueError:
                    stats_secondary.add('Error decoding JSON', package.name)
                    if secondary.startswith('{') and secondary.endswith('}'):
                        new_secondary = secondary[1:-1] # '{Crime}' -> 'Crime'
                    else:
                        del package.extras['theme-secondary']
                        continue

                if new_secondary != secondary:
                    stats_secondary.add('Fixed (long form / to list)', package.name)
                    package.extras['theme-secondary'] = json.dumps(new_secondary)
                else:
                    stats_secondary.add('Ok', package.name)
            else:
                stats_secondary.add('No secondary theme', package.name)

        print "\nPrimary theme:"
        print stats_primary.report()
        print "\nSecondary theme:"
        print stats_secondary.report()

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
    parser.add_option('-o', '--organization', dest='organization')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    FixThemes.command(config_ini, options)
