###############################################################################
# Uses a CSV export from DGU Drupal to determine which datasets are owned by
# which publishers.
#
# Iterates through all of the published_via extras for packages and then if it
# is empty tries the published_by for that package.  Assuming we find something we
# lookup the ID of the publisher (using the CSV instead of trusting the name) and
# associate them.
#
# CSV is generated with:
#
# SELECT
#  distinct
#  DI.ckan_id as 'dataset_id',
#  (SELECT title FROM dgu_drupal.node_revisions
#  AS rr
#  WHERE rr.nid = K.field_publisher_nid ) AS 'publisher_title'
# FROM dgu_drupal.content_type_ckan_package as K
# INNER JOIN dgu_drupal.ckan_package as DI ON DI.nid = K.nid
# ORDER BY 'publisher_title'
# LIMIT 100000;
#
###############################################################################

import os
import logging
import sys
import re
import ckan
import uuid
from ckan import model
from ckan.lib.search import rebuild
from ckan.lib.munge import munge_title_to_name
from sqlalchemy import engine_from_config


def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command():
    import csv
    from pylons import config

    load_config( os.path.abspath( sys.argv[1] ) )
    engine = engine_from_config(config,'sqlalchemy.')

    model.init_model(engine)
    model.repo.new_revision()

    publishers = {  }
    with open(sys.argv[2], 'rU') as f:
        reader = csv.reader( f)
        reader.next() # skip headers
        for row in reader:
            publishers[ int(row[0]) ] = munge_title_to_name(row[1])

    # Check whether
    with_name = re.compile("^.*\[(\d+)\].*$")
    current_data = model.Session.query("package_id", "value")\
                    .from_statement(DATASET_EXTRA_QUERY_VIA).all()

    count = 0
    for p,v in current_data:
        value = v.strip("\"'")
        if not value:
            # blank value == no publisher so we should check the published_BY
            new_v = model.Session.query("value")\
                    .from_statement(DATASET_EXTRA_QUERY_BY).params(package_id=p).all()
            if new_v:
                value = new_v[0][0]
                value = value.strip("\"'")
                if not value:
                    count = count + 1
                    continue

        # Use the with_name regex to strip out the number from something
        # of the format "Name of the publisher [extra_id]"
        g = with_name.match(value)
        if g:
            value = g.groups(0)[0]
        else:
            print value

        # We want to use ints for the lookup, just because
        value = int(value)

        # We don't handle unknown publishers but these should not exist as
        # we are looking from a shared datasource (i.e. publishers published
        # from same list).
        if not value in publishers:
            continue

        member_id          = unicode(uuid.uuid4())
        member_revision_id = unicode(uuid.uuid4())
        revision_id        = unicode(uuid.uuid4())

        # We could optimise here, but seeing as the script currently runs adequately fast
        # we won't bother with caching the name->id lookup
        ids = model.Session.query("id")\
                    .from_statement("select id from public.group where name='%s'" % publishers[value]).all()
        publisher_id = ids[0][0]

        memberq      = MEMBER_QUERY.strip() % \
                        (member_id, p, publisher_id, revision_id)
        member_rev_q = MEMBER_REVISION_QUERY.strip() % \
                        (member_id, p, publisher_id, revision_id, member_id)
        revision_q   = REVISION_QUERY.strip() % (revision_id,)
        print revision_q
        print memberq
        print member_rev_q
        print ''



MEMBER_QUERY = """
INSERT INTO public.member(id, table_id,group_id, state,revision_id, table_name, capacity)
    VALUES ('%s', '%s', '%s', 'active', '%s', 'group', 'member');
"""
MEMBER_REVISION_QUERY = """
INSERT INTO public.member_revision(id, table_id, group_id, state, revision_id, table_name,
                                      capacity, revision_timestamp, current, continuity_id)
    VALUES ('%s', '%s', '%s', 'active', '%s', 'group', 'member',
            '2012-02-17',  true, '%s');
"""
REVISION_QUERY = """
INSERT INTO public.revision(id, timestamp, author, message, state, approved_timestamp)
    VALUES ('%s','2012-02-17', 'admin', 'Migration task', 'active',
            '2012-02-17');
"""

DATASET_EXTRA_QUERY_VIA = \
    "select package_id, value from package_extra where key='published_via'"
DATASET_EXTRA_QUERY_BY = \
    "select value from package_extra where key='published_by' and package_id=:package_id"



def usage():
    print """
Usage:
  Associates publishers with datasets from the provided CSV and using the
  publisher extra property on each dataset in the existing database.

    python publisher_datasets_assoc.py <path to ini file>  <path to nodepublisher csv file>
    """

if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(0)
    command()
