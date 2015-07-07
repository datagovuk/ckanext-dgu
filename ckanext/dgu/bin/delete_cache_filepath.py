'''
Remove no longer used Resouce extra 'cache_filepath'
'''

import common
import json
from optparse import OptionParser
from ckan import model

from running_stats import StatsList

stats = StatsList()


class DeleteCacheFilepath(object):
    @classmethod
    def command(cls, config_ini, write):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'script-delete_cache_filepath.py'
        all_resources = model.Session.query(model.Resource) \
                                     .join(model.ResourceGroup)\
                                     .join(model.Package)\
                                     .filter(model.Package.state == 'active') \
                                     .filter(model.Package.private == False) \
                                     .filter(model.Resource.state == 'active')

        for resource in all_resources:
            if 'cache_filepath' in resource.extras:
                stats.add('Removing cache_filepath', resource.id)
                del resource.extras['cache_filepath']
            else:
                stats.add('No cache_filepath field', resource.id)

        print stats.report()

        if write:
            print 'Writing'
            model.Session.commit()
            print 'Done'

usage = __doc__ + '''
Usage:
    python delete_cache_filepath.py <CKAN config ini filepath> [--write]'''

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
    DeleteCacheFilepath.command(config_ini, options.write)
