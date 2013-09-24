'''
Import/export publishers to/from a CSV file.
'''

import os
import logging
import sys
from sqlalchemy import engine_from_config
import csv
from pylons import config
from nose.tools import assert_equal

import common
from ckanext.dgu.lib import publisher
from ckanext.dgu.forms.validators import categories

categories_dict = dict(categories)

class Publishers(object):
    drupal_client = None
    header = '"id","name","title","parent_publisher_name","parent_publisher_title","abbreviation","wdtk_name","website","contact_email","foi_email","category","spending_published_by"\n'

    @classmethod
    def export(cls, csv_filepath):
        csv_filepath = os.path.abspath(csv_filepath)
        log = global_log

        from ckan import model

        f = open(csv_filepath, 'w')
        f.write(cls.header)

        number_of_publishers = 0
        expected_publishers = set(model.Session.query(model.Group).\
                                  filter_by(state='active').\
                                  filter_by(type='organization').all())
        written_publishers = set()

        for top_level_pub in model.Group.get_top_level_groups(type='organization'):
            for pub in publisher.go_down_tree(top_level_pub):
                number_of_publishers += 1
                if pub in written_publishers:
                    warn('publisher written twice: %s %s', pub.name, pub.id)
                written_publishers.add(pub)
                parent_publishers = pub.get_parent_groups(type='organization')
                if len(parent_publishers) > 1:
                    warn('Publisher has multiple parents. Just using first: %s %s', pub.name, parent_publishers)
                parent_pub_name = parent_publishers[0].name if parent_publishers else ''
                parent_pub_title = parent_publishers[0].title if parent_publishers else ''
                wdtk_id = ''#pub.extras
                csv_row_values = \
                           (pub.id,
                            pub.name,
                            pub.title,
                            parent_pub_name,
                            parent_pub_title,
                            dict(pub.extras).get('abbreviation', ''),
                            dict(pub.extras).get('wdtk-title', ''),
                            dict(pub.extras).get('website-url', ''),
                            dict(pub.extras).get('contact-email', ''),
                            dict(pub.extras).get('foi-email', ''),
                            dict(pub.extras).get('category', ''),
                            dict(pub.extras).get('spending_published_by', ''),
                            )
                # assume they are all strings
                csv_row_str = ','.join(['"%s"' % cell for cell in csv_row_values])
                log.info(csv_row_str)
                f.write(csv_row_str.encode('utf8') + '\n')
                f.flush()

        f.close()

        # checks
        expected_number_of_publishers = len(expected_publishers)
        assert_equal(sorted(written_publishers), sorted(set(written_publishers)))
        assert_equal(expected_publishers, set(written_publishers))

    @classmethod
    def import_(cls, csv_filepath):
        log = global_log

        from ckan import model

        pub_categories = csv.reader(open(csv_filepath, 'rb'))
        header = pub_categories.next()
        assert_equal('"%s"\n' % '","'.join(header), cls.header)
        for id, name, title, parent_name, category, spending_published_by in pub_categories:
            pub = model.Session.query(model.Group).get(id) or \
                  model.Group.by_name(name)

            if not pub:
                log.info('Adding publisher: %s', title)
                cls.add_publisher(id, name, title, parent_name)
                continue

            # set category
            existing_category = pub.extras.get('category')
            if not category:
                #log.info('No categories for %r', title)
                continue
            if category not in categories_dict.keys():
                warn('Category not known %s - skipping %s %s',
                     category, id, title)
                continue
            if existing_category != category:
                log.info('Changing category %r %s -> %s',
                         title, existing_category or '(none)', category)
                model.repo.new_revision()
                pub.extras['category'] = category
                model.Session.commit()
            else:
                #log.info('Leaving category for %r as %s', title, category)
                pass

            # set spending_published_by
            existing_spb = pub.extras.get('spending_published_by')
            if not spending_published_by:
                #log.info('No spending_published_by for %r', title)
                continue
            spb_publisher = model.Group.get(spending_published_by)
            if not spb_publisher:
                spb_publisher = model.Group.search_by_name_or_title(spending_published_by).first()
                if not spb_publisher:
                    warn('Spending_published_by not known %s - skipping %s %s',
                         spending_published_by, id, title)
                    continue
            spending_published_by = spb_publisher.name
            if existing_spb != spending_published_by:
                log.info('Changing SPB %r %s -> %s',
                         title, existing_spb or '(none)', spending_published_by)
                model.repo.new_revision()
                pub.extras['spending_published_by'] = spending_published_by
                model.Session.commit()
            else:
                log.info('Leaving SPB for %r as %s', title, spending_published_by)

        model.Session.remove()

        log.info('Warnings: %r', warnings)

    @classmethod
    def setup_logging(cls, config_ini_filepath):
        logging.config.fileConfig(config_ini_filepath)
        log = logging.getLogger(os.path.basename(__file__))
        global global_log
        global_log = log

    @classmethod
    def add_publisher(cls, id, name, title, parent_name):
        '''Adds a new publisher using the details'''
        from ckan import model
        from ckan.lib.munge import munge_title_to_name

        log = global_log

        model.repo.new_revision()
        g = model.Group(name=name, title=title)
        model.Session.add(g)

        g.id = id
        g.type='organization'
        ## g.extras['contact-name'] = '%s contact' % field_pub_web_title if field_pub_web_title else ''
        ## g.extras['contact-email'] = pub['field_pub_email_display'][0]['email'] if pub['field_pub_email_display'] else ''
        ## g.extras['contact-phone'] = ''
        ## g.extras['foi-name'] = ''
        ## g.extras['foi-email'] = ''
        ## g.extras['foi-phone'] = ''
        ## acronym = pub['field_acronym'][0]['value'] if pub['field_acronym'] else ''
        ## g.extras['abbreviation'] = acronym or ''
        ## g.extras['website-url'] = (pub['field_pub_web'][0]['url'] or '') if pub['field_pub_web'] else ''
        ## g.extras['website-name'] = (pub['field_pub_web'][0]['title'] or '') if pub['field_pub_web'] else ''
        model.Session.commit()

        if parent_name:
            parent = model.Group.get(parent_name)
            if not parent:
                log.error('Could not add parent that does not exist: %s',
                          parent_name)

            else:
                if model.Session.query(model.Member).\
                       filter(model.Member.group==parent).\
                       filter(model.Member.table_id==g.id).count() == 0:
                    m = model.Member(group=parent, table_id=g.id,
                                    table_name='group')
                    model.Session.add(m)
                    log.info('%s is parent of %s', parent_name, g.name)
                else:
                    log.info('%s is already a parent of %s', parent_name, g.name)
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
Import/export publishers to/from a CSV file.
Usage:

  python publisher_sync.py <CKAN config ini filepath> export publishers.csv
    - produces a list of publishers with partial details

  python publisher_sync.py <CKAN config ini filepath> import publishers.csv
    - import a list of publishers to create or update publisher details
    """

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'Wrong number of arguments %i' % len(sys.argv)
        usage()
        sys.exit(0)
    cmd, config_ini, action, filepath = sys.argv
    common.load_config(config_ini)
    Publishers.setup_logging(config_ini)
    common.register_translator()
    if action == 'export':
        Publishers.export(filepath)
    elif action == 'import':
        Publishers.import_(filepath)
    else:
        raise NotImplementedError
