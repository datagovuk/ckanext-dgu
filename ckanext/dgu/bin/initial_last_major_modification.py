'''
This script adds to all datasets an extra called last_major_modification,
defined as the datetime when a resource was last added or deleted, or when a
resource url was last changed.
'''
import sys
import os
import datetime
import logging

import common
from running_stats import StatsList

log = __import__("logging").getLogger(__name__)

class Tool:
    def set_initial_value(self):
        log = global_log
        stats = StatsList()

        from ckan import model
        import ckan.plugins as p
        from ckan.logic import ActionError
        from ckanext.dgu.lib.helpers import upsert_extra

        site_user = p.toolkit.get_action('get_site_user')({'model': model,'ignore_auth': True}, {})
        c = {'model': model, 'user': site_user['name']}
        packages = p.toolkit.get_action('package_list')(c, data_dict={})
        
        log.info('Processing %d packages', len(packages))

        for pkg_name in packages:
            pkg = model.Package.by_name(pkg_name)

            last_mod = self.determine_last_major_modification(pkg).isoformat()
            log.info('%s: %s %s', pkg_name, pkg.extras.get('last_major_modification'), last_mod)
            if pkg.extras.get('last_major_modification') != last_mod:
                log.info(stats.add('Adding modification date', pkg.name))
                model.repo.new_revision()
                pkg.extras['last_major_modification'] = last_mod
                model.repo.commit_and_remove()
            else:
                log.info(stats.add('No change needed', pkg.name))
        print stats.report()

    @staticmethod
    def determine_last_major_modification(pkg):
        from ckan import model
        # Query for a resource's first revision
        first_res_rev_q = model.Session.query(model.ResourceRevision)\
                          .order_by(model.ResourceRevision.revision_timestamp)
        # Get this package's resource revisions, latest first.
        resource_revisions = model.Session.query(model.ResourceRevision)\
                             .join(model.ResourceGroup)\
                             .join(model.Package)\
                             .filter(model.Package.id==pkg.id)\
                             .order_by(model.ResourceRevision.revision_timestamp.desc())
        resource_urls = {} # res_id: (url, state, date)
        # Look for a revision where the URL or state changed or revision
        # was created
        for res_rev in resource_revisions:
            if res_rev.id in resource_urls:
                url, state, date_ = resource_urls[res_rev.id]
                if res_rev.url != url or res_rev.state != state:
                    # URL changed
                    return date_
            resource_urls[res_rev.id] = (res_rev.url, res_rev.state,
                                         res_rev.revision_timestamp)
            # Unfortunately can't use res_rev.created to see when the first
            # revision was. res_rev.created was datetime.now() when the object
            # was created, and the first revision_timestamp was datetime.nowutc()
            # when new_revision was run - so *about* 0 or 60 minutes different.
            first_res_rev = first_res_rev_q\
                            .filter(model.ResourceRevision.id==res_rev.id).first()
            if first_res_rev is res_rev:
                # this resource was created in this revision
                return res_rev.revision_timestamp

        return pkg.metadata_created
        
    @classmethod
    def setup_logging(cls, config_ini_filepath):
        logging.config.fileConfig(config_ini_filepath)
        log = logging.getLogger(os.path.basename(__file__))
        global global_log
        global_log = log

def usage():
    print """
Sets the 'last_major_modification' extra on all packages.

Usage:

  python initial_last_major_modification <CKAN config ini filepath>
    """

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Wrong number of arguments %i' % len(sys.argv)
        usage()
        sys.exit(1)
    cmd, config_ini = sys.argv
    common.load_config(config_ini)
    Tool.setup_logging(config_ini)
    common.register_translator()
    Tool().set_initial_value()
