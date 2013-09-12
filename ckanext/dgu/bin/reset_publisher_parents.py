'''
Publishers not assigned a parent will be assigned one using Drupal\'s hierarchy of publishers, got from the XMLRPC interface.
'''

import os
import logging
import sys
from sqlalchemy import engine_from_config
import csv
from pylons import config
from nose.tools import assert_equal

from import_publishers2 import ignore_publishers
from ckanext.dgu.bin import status

class ImportPublisherTree(object):
    publisher_cache = {} # {nid:publisher_details}
    drupal_client = None

    @classmethod
    def load_config(cls, path):
        import paste.deploy
        conf = paste.deploy.appconfig('config:' + path)
        import ckan
        ckan.config.environment.load_environment(conf.global_conf,
                conf.local_conf)

    @classmethod
    def command(cls, config_ini):
        config_ini_filepath = os.path.abspath(config_ini)
        cls.load_config(config_ini_filepath)
        engine = engine_from_config(config, 'sqlalchemy.')

        from ckan import model
        from ckanext.dgu.drupalclient import DrupalClient, log as drupal_client_log

        drupal_client_log.disabled = True

        logging.config.fileConfig(config_ini_filepath)
        log = logging.getLogger(os.path.basename(__file__))
        global global_log
        global_log = log

        cls.status = status.Status()
        model.init_model(engine)
        model.repo.new_revision()

        cls.drupal_client = DrupalClient({'xmlrpc_domain': 'data.gov.uk',
                                          'xmlrpc_username': 'CKAN_API',
                                          'xmlrpc_password': config.get('dgu.xmlrpc_password')})
        publisher_dicts = cls.drupal_client.get_organisation_list()

        for publisher_dict in publisher_dicts:
            if not (publisher_dict['status'] == '1' or \
                    publisher_dict['nid'] == '16248'):
                # Make an exception for 16248 - Met Office under BIS is correct
                cls.status.record('Unpublished in Drupal', publisher_dict['title'], do_print=False)
                log.info('Ignoring unpublished publisher with status %r: %r',
                         publisher_dict['status'], publisher_dict)
                continue

            publisher_nid = publisher_dict['nid']
            if int(publisher_nid) in ignore_publishers:
                cls.status.record('On "ignore" list', publisher_dict['title'], do_print=False)
                global_log.info('Publisher ignored: %s', publisher_nid)
                continue

            cls.do_publisher(publisher_nid)

        all_groups = model.Session.query(model.Group).\
                           filter(model.Group.type == 'organization').order_by('title').all()
        log.info('Total number of groups: %i', len(all_groups))
        log.info('Warnings: %r', warnings)

        print cls.status

    @classmethod
    def get_cached_publisher_details(cls, publisher_nid):
        if publisher_nid not in cls.publisher_cache:
            cls.publisher_cache[publisher_nid] = cls.drupal_client.get_organisation_details(publisher_nid)
        return cls.publisher_cache[publisher_nid]

    @classmethod
    def do_publisher(cls, publisher_nid):
        from ckan import model
        from ckan.lib.munge import munge_title_to_name
        log = global_log

        pub = cls.get_cached_publisher_details(publisher_nid)

        title = pub['title'].strip()

        slug = munge_title_to_name(title)
        g = model.Group.get(slug)
        if g:
            log.info('Found publisher in db: %s', g.name)
        else:
            cls.status.record('Not found in CKAN db', slug, do_print=False)
            log.warn('Ignoring publisher that cannot be found in db: %s', slug)
            return

        if pub.get('parent_node'):
            parent_pub_title = cls.get_cached_publisher_details(pub['parent_node'])['title']
            parent_name = munge_title_to_name(parent_pub_title)
            parent = model.Group.get(parent_name)
            if not parent:
                cls.status.record('Cannot find parent in CKAN db', g.name, do_print=False)
                log.warning('Cannot find parent %s of %s', parent_name, pub.name)
                return

            existing_parents = [m.group for m in model.Session.query(model.Member).\
                                filter(model.Member.table_name=='group').\
                                filter(model.Member.table_id==g.id).\
                                filter(model.Member.state=='active')]
            if existing_parents:
                if len(existing_parents) > 1:
                    log.warn('Multiple parents for %s: %r', g.name,
                             [p.name for p in existing_parents])
                if parent in existing_parents:
                    cls.status.record('Correct parent already',
                                       g.name, do_print=False)
                    log.info('Correct parent already: %s parent of %s',
                             parent.name, g.name)
                    return
                else:
                    cls.status.record('Has another parent',
                                       g.name, do_print=False)
                    log.info('Has another parent: %r (instead of %s) parent of %s',
                             [p.name for p in existing_parents], parent.name, g.name)
                    return

            m = model.Member(group=parent, table_id=g.id, table_name='group')
            model.Session.add(m)
            model.Session.commit()
            cls.status.record('Parent added', slug, do_print=False)
            log.info('%s is made parent of %s', parent.name, g.name)
        else:
            log.info('%s has no parent in Drupal' % g.name)
            cls.status.record('Has no parent in Drupal',
                               g.name, do_print=False)


warnings = []
global_log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    global_log.warn(msg, *params)


def usage():
    print """
Imports publishers from the specified CSV file.
Usage:

    python import_publishers.py <CKAN config ini filepath>
    """

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit(0)
    cmd, config_ini= sys.argv
    ImportPublisherTree.command(config_ini)
