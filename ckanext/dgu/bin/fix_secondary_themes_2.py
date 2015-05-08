'''
Fix the multiple JSON encoding of the secondary theme extra

e.g.

'"\\"Health\\""' -> '["Health"]'
'Towns & Cities' -> '["Towns & Cities"]'
'"Government, Society"' -> '["Government", "Society"]'
'None' -> '[]'
'[\"None\"]' -> '[]'
'''

import json
from optparse import OptionParser

import common
from running_stats import Stats

stats_format = Stats()
stats_outcome = Stats()


class FixSecondaryTheme2(object):
    @classmethod
    def command(cls, options):
        from ckan import model
        if options.write:
            rev = model.repo.new_revision()
            rev.author = 'script_fix_secondary_themes_2.py'

        datasets = common.get_datasets(state='active',
                                       dataset_name=options.dataset)
        for package in datasets:
            if not 'theme-secondary' in package.extras:
                stats_outcome.add('Ignore - no secondary theme', package.name)
                continue

            secondary_theme = package.extras.get('theme-secondary')

            loop = 1
            while isinstance(secondary_theme, basestring):
                try:
                    secondary_theme = json.loads(secondary_theme)
                except ValueError:
                    if secondary_theme == 'None':
                        stats_format.add('"None" string', package.name)
                        secondary_theme = []
                    elif ',' in secondary_theme:
                        # e.g. '"Government, Society"'
                        print stats_format.add('Non-JSON string, comma separated', package.name)
                        secondary_theme = [t.strip() for t in secondary_theme.split(',')]
                    else:
                        # e.g. 'Towns & Cities'
                        print stats_format.add('Non-JSON string', '%s %r' % (package.name, secondary_theme.strip()))
                        secondary_theme = [secondary_theme.strip()]
                    break
                loop = 1
                if loop == 2:
                    stats_format.add('JSON', package.name)
                elif loop == 3:
                    # e.g. '"\\"Health\\""'
                    print stats_format.add('Multiple JSON encoded', package.name)

            for filter_string in (None, 'None', ''):
                if filter_string in secondary_theme:
                    print stats_format.add('%r in the list' % filter_string, package.name)
                    secondary_theme = [theme for theme in secondary_theme
                                       if theme != filter_string]

            if json.dumps(secondary_theme) != package.extras.get('theme-secondary'):
                stats_outcome.add('Fixing', package.name)
                if secondary_theme == 'None' or secondary_theme == '':
                    stats_format.add(secondary_theme, package.name)
                    package.extras['theme-secondary'] = json.dumps([])
                else:
                    package.extras['theme-secondary'] = json.dumps(secondary_theme)
            else:
                stats_outcome.add('Unchanged', package.name)

        print 'Formats:\n', stats_format.report()
        print 'Outcomes:\n', stats_outcome.report()

        if options.write:
            print 'Writing...'
            model.Session.commit()
            print '...done'



usage = '''
    python %prog $CKAN_INI
'''

if __name__ == '__main__':
    parser = OptionParser(description=__doc__.strip(), usage=usage)
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes to the datasets")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]

    common.load_config(config_ini)
    common.register_translator()
    FixSecondaryTheme2.command(options)
