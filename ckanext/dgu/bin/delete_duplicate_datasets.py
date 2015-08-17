'''
Delete duplicate datasets caused by harvesting bug

http://redmine.dguteam.org.uk/issues/1861
'''

import sys
import common
from optparse import OptionParser
from collections import defaultdict
from ckan import model

from running_stats import StatsList

stats = StatsList()

class DeleteDuplicateDatasets(object):
    @classmethod
    def command(cls, config_ini, write):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'script_delete_duplicate_datasets.py'

        publisher = model.Group.get(options.publisher)
        if publisher is None:
            print "Publisher could not be found"
            sys.exit(0)

        guids = defaultdict(list)
        for package in publisher.packages():
            guids[package.extras.get('guid')].append(package)

        for guid, packages in guids.items():
            for i, package in enumerate(sorted(packages,
                                               key=lambda x: x.metadata_modified,
                                               reverse=options.keep_last)):
                if i == 0:
                    stats.add('Skipping', package.name)
                else:
                    stats.add('Deleting', package.name)
                    package.state = 'deleted'

        if write:
            model.Session.commit()

        print stats.report()


def usage():
    print """
Delete duplicate datasets

Usage:

    python delete_duplicate_datasets.py <CKAN config ini filepath> -p <publisher>
    """

if __name__ == '__main__':
    parser = OptionParser(usage='')
    parser.add_option('-p', '--publisher', dest='publisher')
    parser.add_option('-k', '--keep-last', dest='keep_last', default=True)
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

    if options.publisher is None:
        print "You must specify a publisher to work on"
        sys.exit(0)

    print options.keep_last

    DeleteDuplicateDatasets.command(config_ini, options.write)
