'''
Imports the DGU Publisher hierarchy from Drupal\'s hierarchy of publishers using the XMLRPC interface.
'''

import os
import logging
import sys
from sqlalchemy import engine_from_config
import csv
from pylons import config
from nose.tools import assert_equal

# These publishers must have been created by mistake - don't transfer to CKAN
ignore_publishers = (28266, #'Hazel Lee'
                     28267, #'George Wilson'
                     16268, # "Office OF" repeats ONS, sub-pub of correct 11408
                     11606, # ONS repeat
                     20054, # Met Office repeat of 16248, falsely under MoD
                     33036, # "Royal Borough of Windsor and Maidenhead" repeat
                     32619, # "Monmouthshire County Council" under Welsh Government
                     36487, # 'Paul Lyons'
                     36488, # 'Barbara Lennards'
                     34613, # 'Iain Sharp'
                     11539, # 'None'
                     12662, # 'NHS' (duplicate of fuller title)
                     38309, # 'Ian Parfitt'
                     )

class ImportPublishers(object):
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
        from ckanext.dgu.drupalclient import DrupalClient

        logging.config.fileConfig(config_ini_filepath)
        log = logging.getLogger(os.path.basename(__file__))
        global global_log
        global_log = log

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
                log.info('Ignoring unpublished publisher with status %r: %r',
                         publisher_dict['status'], publisher_dict)
                continue
            cls.add_publisher(publisher_dict['nid'])

        all_groups = model.Session.query(model.Group).\
                           filter(model.Group.type == 'organization').order_by('title').all()
        log.info('Total number of groups: %i', len(all_groups))
        log.info('Warnings: %r', warnings)

    @classmethod
    def get_cached_publisher_details(cls, publisher_nid):
        if publisher_nid not in cls.publisher_cache:
            cls.publisher_cache[publisher_nid] = cls.drupal_client.get_organisation_details(publisher_nid)
        return cls.publisher_cache[publisher_nid]

    @classmethod
    def add_publisher(cls, publisher_nid):
        from ckan import model
        from ckan.lib.munge import munge_title_to_name

        if int(publisher_nid) in ignore_publishers:
            global_log.info('Publisher ignored: %s (%s)', publisher_nid,
                            cls.get_cached_publisher_details(publisher_nid))
            return

        pub = cls.get_cached_publisher_details(publisher_nid)

        title = pub['title'].strip()

        slug = munge_title_to_name(title)
        g = model.Group.get(slug)
        if g:
            global_log.info('Publisher already exists in db: %s', slug)
        else:
            g = model.Group(name=slug)
            model.Session.add(g)

        g.title=title
        g.type='publisher'
        g.description=pub['body']
        field_pub_web_title = pub['field_pub_web'][0]['title'] if pub['field_pub_web'] else ''
        g.extras['contact-name'] = '%s contact' % field_pub_web_title if field_pub_web_title else ''
        g.extras['contact-email'] = pub['field_pub_email_display'][0]['email'] if pub['field_pub_email_display'] else ''
        g.extras['contact-phone'] = ''
        g.extras['foi-name'] = ''
        g.extras['foi-email'] = ''
        g.extras['foi-phone'] = ''
        acronym = pub['field_acronym'][0]['value'] if pub['field_acronym'] else ''
        g.extras['abbreviation'] = acronym or ''
        g.extras['website-url'] = (pub['field_pub_web'][0]['url'] or '') if pub['field_pub_web'] else ''
        g.extras['website-name'] = (pub['field_pub_web'][0]['title'] or '') if pub['field_pub_web'] else ''
        model.Session.commit()
        title_and_abbreviation = '%s (%s)' % (title, acronym) if acronym else title
        global_log.info('Added/edited publisher: %s <%s>', title_and_abbreviation, publisher_nid)

        if pub.get('parent_node'):
            parent_pub_title = cls.get_cached_publisher_details(pub['parent_node'])['title']
            parent = model.Group.get(munge_title_to_name(parent_pub_title))
            if not parent:
                parent = cls.add_publisher(pub['parent_node'])

            if model.Session.query(model.Member).\
                filter(model.Member.group==parent).\
                filter(model.Member.table_id==g.id).count() == 0:
                m = model.Member(group=parent, table_id=g.id, table_name='group')
                model.Session.add(m)
                global_log.info('%s is parent of %s', parent.name, g.name)
            else:
                global_log.info('%s is already a parent of %s', parent.name, g.name)
            model.Session.commit()

        return g


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
    ImportPublishers.command(config_ini)
