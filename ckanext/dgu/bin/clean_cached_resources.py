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

from ckanext.dgu.bin import running_stats

DEFAULT_CACHE_DIR = '/media/hulk/ckan_resource_cache/'

stats = running_stats.StatsWithSum()

class CleanCachedResources(object):
    @classmethod
    def command(cls, config_ini, cache_dir, delete_files):
        common.load_config(config_ini)
        common.register_translator()

        #rev = model.repo.new_revision()
        #rev.author = 'fix_secondary_theme.py'

        files_to_delete = []
        count = 0
        for f in glob.iglob(os.path.join(cache_dir, '*/*/*')):
            a = model.Session.query(Archival).filter(Archival.cache_filepath==f).first()
            size = os.path.getsize(f)
            if a == None:
                print stats.add('Not in archival table', f.decode('utf8'), size)
                files_to_delete.append(f)
            else:
                res = model.Resource.get(a.resource_id)
                if not res:
                    print stats.add('No matching resouce', f.decode('utf8'), size)
                    files_to_delete.append(f)
                elif res.state == 'deleted':
                    print stats.add('Resource is deleted', f.decode('utf8'), size)
                    files_to_delete.append(f)
                else:
                    pkg = res.resource_group.package
                    if pkg.state == 'deleted':
                        print stats.add('Package is deleted', f.decode('utf8'), size)
                        files_to_delete.append(f)
                    else:
                        print stats.add('OK', f.decode('utf8'), size)

            count += 1
            if count % 250 == 0:
                print '\n\n\nProgress after %s:' % count
                print stats.report()
                print '\n\n'

        print stats.report()

        if delete_files:
            print 'Deleting %s files' % len(files_to_delete)
            for f in files_to_delete:
                try:
                    os.unlink(f)
                except OSError:
                    stats.add('Error Deleting', f.decode('utf8'))
        print 'Done'


def usage():
    print """
    python clean_cached_resources.py <CKAN config ini filepath>
    """

if __name__ == '__main__':
    parser = OptionParser(usage='')
    parser.add_option("-d", "--delete-files",
                      action="store_true",
                      dest="delete_files",
                      default=False,
                      help="delete unrequired cached resources")
    parser.add_option("-c", "--cachedir",
                      dest="cache_dir",
                      default=DEFAULT_CACHE_DIR)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        usage()
        sys.exit(0)
    config_ini = args[0]

    if options.cache_dir != DEFAULT_CACHE_DIR:
        if not os.path.exists(os.path.join(options.cache_dir, '00')):
            print "Are you sure you have the right directory?"
            sys.exit(0)

    CleanCachedResources.command(config_ini, options.cache_dir, options.delete_files)
