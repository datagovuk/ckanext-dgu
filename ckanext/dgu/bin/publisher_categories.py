'''
Fills in the category field for publishers
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
from running_stats import Stats

categories_dict = dict(categories)

class PublisherCategories(object):
    publisher_cache = {} # {nid:publisher_details}
    drupal_client = None
    header = '"id","title","parent_publisher","category","spending_published_by"\n'

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
                parent_pub_title = top_level_pub.title if top_level_pub.id != pub.id else ''
                csv_line = '"%s","%s","%s","%s","%s"' % \
                           (pub.id,
                            pub.title,
                            parent_pub_title,
                            dict(pub.extras).get('category', ''),
                            dict(pub.extras).get('spending_published_by', ''),
                            )
                log.info(csv_line)
                f.write(csv_line + '\n')
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
        stats_category = Stats()

        pub_categories = csv.reader(open(csv_filepath, 'rb'))
        header = pub_categories.next()
        assert_equal('"%s"\n' % '","'.join(header), cls.header)
        for id, title, parent, category, spending_published_by in pub_categories:
            pub = model.Session.query(model.Group).get(id)
            if not pub:
                print stats_category.add('Publisher ID not known', '%s %s' % (id, title))
                continue
            category = category.strip()

            # set category
            existing_category = pub.extras.get('category')
            if not category and not existing_category:
                print stats_category.add('No category info - ignored', title)
                continue
            if not category and existing_category:
                print stats_category.add('Category deleted', '%s %s' % (existing_category, title))
                rev = model.repo.new_revision()
                rev.author = 'script_' + __file__
                pub.extras['category'] = None
                model.Session.commit()
                continue
            if category not in categories_dict.keys():
                print stats_category.add('Category %s not known - ignored' % category, title)
                continue
            if existing_category != category:
                print stats_category.add('Changing category',
                    '%s->%s %s' % (existing_category or '(none)', category, title))
                rev = model.repo.new_revision()
                rev.author = 'script_' + __file__
                pub.extras['category'] = category
                model.Session.commit()
            else:
                print stats_category.add('No change',
                        '%s %s' % (existing_category or '(none)', title))
                log.info('Leaving category for %r as %s', title, category)

            # set spending_published_by
            existing_spb = pub.extras.get('spending_published_by')
            if not spending_published_by:
                log.info('No spending_published_by for %r', title)
                continue
            spb_publisher = model.Group.get(spending_published_by)
            if not spb_publisher:
                spb_publisher = model.Group.search_by_name_or_title(spending_published_by)
                if not spb_publisher:
                    warn('Spending_published_by not known %s - skipping %s %s',
                         spending_published_by, id, title)
                    import pdb; pdb.set_trace()
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

        print stats_category
        log.info('Warnings: %r', warnings)

    @classmethod
    def setup_logging(cls, config_ini_filepath):
        logging.config.fileConfig(config_ini_filepath)
        log = logging.getLogger(os.path.basename(__file__))
        global global_log
        global_log = log

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
        g.extras['foi-web'] = ''
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

  python publisher_categories.py <CKAN config ini filepath> export pub_cats.csv
    - produces a list of publishers and their categories

  python publisher_categories.py <CKAN config ini filepath> import pub_cats.csv
    - import an amended list of publishers and their categories
    """

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'Wrong number of arguments %i' % len(sys.argv)
        usage()
        sys.exit(0)
    cmd, config_ini, action, filepath = sys.argv
    common.load_config(config_ini)
    PublisherCategories.setup_logging(config_ini)
    common.register_translator()
    if action == 'export':
        PublisherCategories.export(filepath)
    elif action == 'import':
        PublisherCategories.import_(filepath)
    else:
        raise NotImplementedError
