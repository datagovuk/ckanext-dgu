'''
'''

import os
import sys
import glob
from itertools import chain
import ckanext.dgu.bin.common as common
from optparse import OptionParser
from ckan import model
from ckanext.archiver.model import Archival

from ckanext.dgu.bin.running_stats import StatsList

DEFAULT_CACHE_DIR = '/media/hulk/ckan_resource_cache/'

stats = StatsList()

class CleanCachedResources(object):
    @classmethod
    def command(cls, config_ini, cache_dir, delete):
        common.load_config(config_ini)
        common.register_translator()

        #rev = model.repo.new_revision()
        #rev.author = 'fix_secondary_theme.py'

        no_archival = []
        deleted_res = []
        for f in glob.glob(os.path.join(cache_dir, '*/*/*')):
            a = model.Session.query(Archival).filter(Archival.cache_filepath==f).first()
            if a == None:
                stats.add('No archival', f.decode('utf8'))
                no_archival.append(f)
            else:
                res = model.Resource.get(a.resource_id)
                if res.state == 'deleted':
                    stats.add('Deleted Resouce', f.decode('utf8'))
                    deleted_res.append(f)
                else:
                    stats.add('OK', f.decode('utf8'))

        if delete:
            for f in chain(deleted_res, no_archival):
                try:
                    os.unlink(f)
                except OSError:
                    stats.add('Error Deleting', f.decode('utf8'))

        #with open('no-archival.txt', 'w') as outfile:
        #    for f in no_archival:
        #        outfile.write("%s\n" % f)

        #with open('deleted-res.txt', 'w') as outfile:
        #    for f in deleted_res:
        #        outfile.write("%s\n" % f)

        print stats.report()


def usage():
    print """
    python clean_cached_resources.py <CKAN config ini filepath>
    """

if __name__ == '__main__':
    parser = OptionParser(usage='')
    parser.add_option("-d", "--delete",
                      action="store_true",
                      dest="delete",
                      default=False,
                      help="delete unrequired cached resources")
    parser.add_option("-c", "--cachedir",
                      dest="cache_dir",
                      default=DEFAULT_CACHE_DIR,
                      help="delete unrequired cached resources")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        usage()
        sys.exit(0)
    config_ini = args[0]

    if options.cache_dir != DEFAULT_CACHE_DIR:
        if not os.path.exists(os.path.join(options.cache_dir, '00')):
            print "Are you sure you have the right directory?"
            sys.exit(0)

    CleanCachedResources.command(config_ini, options.cache_dir, options.delete)
