'''
'''

import os
import sys
import glob
from itertools import chain
import ckanext.dgu.bin.common as common
from argparse import ArgumentParser
from ckan import model
from ckanext.packagezip.model import PackageZip

from ckanext.dgu.bin import running_stats

DEFAULT_PACKAGE_ZIP_DIR = '/media/hulk/packagezip/'

stats = running_stats.StatsWithSum()

class CleanCachedResources(object):
    @classmethod
    def command(cls, config_ini, package_zip_dir, delete_files):
        common.load_config(config_ini)
        common.register_translator()

        files_to_delete = []
        count = 0
        for f in glob.iglob(os.path.join(package_zip_dir, '*')):
            a = model.Session.query(PackageZip) \
                     .filter(PackageZip.filepath==f) \
                     .first()
            size = os.path.getsize(f)
            if a == None:
                print stats.add('Not in packagezip table', f.decode('utf8'), size)
                files_to_delete.append(f)
            else:
                    pkg = model.Package.get(a.package_id)
                    if pkg.state == 'deleted':
                        print stats.add('Package is deleted', f.decode('utf8'), size)
                        files_to_delete.append(f)
                    else:
                        stats.add('OK', f.decode('utf8'), size)

            count += 1
            if count % 250 == 0:
                print '\n\nProgress after %s:' % count
                print stats.report()

        print stats.report()

        if delete_files:
            print 'Deleting %s files' % len(files_to_delete)
            for f in files_to_delete:
                try:
                    os.unlink(f)
                except OSError:
                    print stats.add('ERROR Deleting', f.decode('utf8'), 0)
        print 'Done'


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('config_ini',
                        help='CKAN config ini filepath')
    parser.add_argument("-d", "--delete-files",
                        action="store_true",
                        dest="delete_files",
                        default=False,
                        help="delete unrequired cached resources")
    parser.add_argument("-c", "--cachedir",
                        dest="cache_dir",
                        default=DEFAULT_PACKAGE_ZIP_DIR)
    args = parser.parse_args()

    if args.cache_dir != DEFAULT_PACKAGE_ZIP_DIR:
        if not os.path.exists(os.path.join(
                args.cache_dir, 'cabinet-office-energy-use.zip')):
            parser.error('Are you sure you have the right directory?')

    CleanCachedResources.command(args.config_ini, args.cache_dir, args.delete_files)
