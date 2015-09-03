'''
Fix some secondary theme problems

e.g.

["[", "\\"", "G", "o", "v", "e", "r", "n", "m", "e", "n", "t", "", "S", "p", "e", "n", "d",     "i", "n", "g", "\\"", "]"] -> ["Government Spending"]

["C", "r", "i", "m", "e", "", "&", "", "J", "u", "s", "t", "i", "c", "e"] -> ["Crime & Justice"]

'''

import json
from optparse import OptionParser

import common
from running_stats import Stats

stats_format = Stats()
stats_outcome = Stats()

LOOKUP = {
    '["[", "]"]': '[]',
    '["[", "\\"", "G", "o", "v", "e", "r", "n", "m", "e", "n", "t", "", "S", "p", "e", "n", "d", "i", "n", "g", "\\"", "]"]': '["Government Spending"]',
    '["[", "\\"", "B", "u", "s", "i", "n", "e", "s", "s", "", "&", "", "E", "c", "o", "n", "o", "m", "y", "\\"", "]"]': '["Business & Economy"]',
    '["[", "", "", "\\"", "", "", "M", "", "", "a", "", "", "p", "", "", "p", "", "", "i", "", "", "n", "", "", "g", "", "", "\\"", "", "", "]"]': '["Mapping"]',
    '["[", "\\"", "M", "a", "p", "p", "i", "n", "g", "\\"", "]"]': '["Mapping"]',
    '["[", "\\"", "E", "n", "v", "i", "r", "o", "n", "m", "e", "n", "t", "\\"", "]"]': '["Environment"]',
    '["[", "\\"", "G", "o", "v", "e", "r", "n", "m", "e", "n", "t", "\\"", "]"]': '["Government"]',
    '["[", "\\"", "B", "u", "s", "i", "n", "e", "s", "s", "", "&", "", "E", "c", "o", "n", "o", "m", "y", "\\"", "", "", "", "\\"", "G", "o", "v", "e", "r", "n", "m", "e", "n", "t", "", "S", "p", "e", "n", "d", "i", "n", "g", "\\"", "", "", "", "\\"", "H", "e", "a", "l", "t", "h", "\\"", "]"]': '["Business & Economy", "Government Spending", "Health"]',
}


class FixSecondaryTheme3(object):
    @classmethod
    def command(cls, options):
        from ckan import model
        if options.write:
            rev = model.repo.new_revision()
            rev.author = 'script_fix_secondary_themes_3.py'

        datasets = common.get_datasets(state='active',
                                       dataset_name=options.dataset)
        for package in datasets:
            if not 'theme-secondary' in package.extras:
                stats_outcome.add('Ignore - no secondary theme', package.name)
                continue

            secondary_theme = package.extras.get('theme-secondary')

            if secondary_theme.startswith('["["'):
                secondary_theme = LOOKUP[secondary_theme]

            secondary_theme = json.loads(secondary_theme)

            if isinstance(secondary_theme, list) and secondary_theme and len(secondary_theme[0]) == 1:
                secondary_theme = "".join(secondary_theme).replace('&', ' & ')
                if secondary_theme == 'GovernmentBusiness & Economy':
                    secondary_theme = ['Government', 'Business & Economy']
                elif secondary_theme == 'GovernmentSpending':
                    secondary_theme = ['Government Spending']
                elif secondary_theme == 'EnvironmentEducationGovernmentSpending':
                    secondary_theme = ['Environment', 'Education', 'Government Spending']
                elif secondary_theme == 'EnvironmentGovernment':
                    secondary_theme = ['Environment', 'Government']
                else:
                    secondary_theme = [secondary_theme]

            if json.dumps(secondary_theme) != package.extras.get('theme-secondary'):
                stats_outcome.add('Fixing', package.name)
 
                package.extras['theme-secondary'] = json.dumps(secondary_theme)
            else:
                stats_outcome.add('Unchanged', package.name)

        print 'Formats:\n', stats_format.report()
        print 'Outcomes:\n', stats_outcome.report()

        if options.write:
            print 'Writing...'
            model.Session.commit()
            print '...done'
            stats_format.show_time_taken()



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
    FixSecondaryTheme3.command(options)
