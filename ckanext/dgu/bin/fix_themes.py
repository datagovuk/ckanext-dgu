'''
Fix the themes

* to long form e.g. Crime -> Crime & Justice
* bad format e.g. {Crime}
* bad theme names recategorized
'''

import common
import json
from optparse import OptionParser

from running_stats import Stats

stats_primary = Stats()
stats_secondary = Stats()
stats_recategorize = Stats()

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

        from ckan import model
        from ckanext.dgu.lib.theme import (categorize_package, PRIMARY_THEME,
                                           SECONDARY_THEMES)
        rev = model.repo.new_revision()
        rev.author = 'script-fix_themes.py'

        datasets = common.get_datasets(state='active',
                                       dataset_name=options.dataset,
                                       organization_ref=options.organization)

        def fix_theme(theme_str):
            '''Returns (fixed_theme_str, outcome)'''
            if not theme_str:
                return '', 'Blank'
            elif theme_str == 'null':
                return '', '"null"->""'
            elif theme_str in THEMES:
                return theme_str, 'Ok'
            else:
                fixed_theme = THEME_MAP.get(theme_str)
                if fixed_theme is None:
                    return theme_str, 'Unknown theme %s - recategorizing' % theme_str
                else:
                    assert(fixed_theme != theme_str)
                    return fixed_theme, 'Changed to long form'
                    package.extras[PRIMARY_THEME] = new_primary

        def recategorize(pkg):
            themes = categorize_package(pkg, stats_recategorize)
            print 'Recategorize: %s' % themes
            if themes:
                pkg.extras[PRIMARY_THEME] = themes[0]
            elif PRIMARY_THEME in pkg.extras:
                pkg.extras[PRIMARY_THEME] = ''
            if len(themes) > 1:
                pkg.extras[SECONDARY_THEMES] = '["%s"]' % themes[1]
            elif SECONDARY_THEMES in pkg.extras:
                pkg.extras[SECONDARY_THEMES] = '[]'

        for package in datasets:
            if PRIMARY_THEME in package.extras:
                primary = package.extras.get(PRIMARY_THEME)
                new_primary, outcome = fix_theme(primary)
                if new_primary != primary:
                    package.extras[PRIMARY_THEME] = new_primary
                output = stats_primary.add(outcome, package.name)
                if outcome != 'Ok':
                    print output
                if outcome.startswith('Unknown theme'):
                    recategorize(package)
                    continue
            else:
                stats_primary.add('No theme', package.name)

            if SECONDARY_THEMES in package.extras:
                secondary = package.extras.get(SECONDARY_THEMES)
                try:
                    secondary = json.loads(secondary)
                except ValueError:
                    if secondary.startswith('{') and secondary.endswith('}'):
                        # '{Crime}' -> 'Crime'
                        secondary = secondary[1:-1].strip('\"')
                        print stats_secondary.add('Tidied {}', package.name)
                    else:
                        print stats_secondary.add('Error decoding JSON', package.name)

                if secondary == {}:
                    secondary = []

                new_secondary = []
                do_recategorize = False

                if not isinstance(secondary, list):
                    secondary = [secondary]
                for theme_str in secondary:
                    if not isinstance(theme_str, basestring):
                        print stats_secondary.add('Not a list of strings %s' % type(theme_str), package.name)
                        continue
                    new_theme, outcome = fix_theme(theme_str)
                    if new_theme:
                        new_secondary.append(new_theme)
                    if outcome != 'Ok':
                        print stats_secondary.add(outcome, package.name)
                    if outcome.startswith('Unknown theme'):
                        do_recategorize = True
                if do_recategorize:
                    recategorize(package)
                    continue
                if json.dumps(new_secondary) != package.extras.get(SECONDARY_THEMES):
                    stats_secondary.add('Fixed', package.name)
                    package.extras[SECONDARY_THEMES] = json.dumps(new_secondary)
                else:
                    stats_secondary.add('Ok', package.name)
            else:
                stats_secondary.add('No theme', package.name)

            if 'themes-secondary' in package.extras:
                print stats_secondary.add('Old key removed: themes-secondary',
                                          '%s %s' % (package.name, package.extras['themes-secondary']))
                del package.extras['themes-secondary']

        print "\nPrimary theme:"
        print stats_primary.report()
        print "\nSecondary theme:"
        print stats_secondary.report()
        print "\nRecategorizations:"
        print stats_recategorize.report()

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
