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
import csv
import re
import ckan
import uuid
from ckan import model
from ckan.lib.search import rebuild
from ckan.lib.munge import munge_title_to_name
from sqlalchemy import engine_from_config
from pylons import config

publishers = {}

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)


def command():
    load_config( os.path.abspath( sys.argv[1] ) )
    engine = engine_from_config(config,'sqlalchemy.')

    model.init_model(engine)
    model.repo.new_revision()

    with open(sys.argv[2], 'rU') as f:
        reader = csv.reader( f)
        reader.next() # skip headers
        for row in reader:
            publishers[ int(row[0]) ] = munge_title_to_name(row[1])

    generate_harvest_publishers()
    update_datasets()


def log_missing_data( id, name, package, first=False ):
    mode = 'wb' if first else 'ab'
    with open('errors.csv', mode) as f:
        if first:
            f.write( 'DGU_Publisher_ID,Extra,Package\r\n' )
        f.write( '%s, %s, "%s"\r\n' % (id, name, package,) )

def generate_harvest_publishers():
    data = model.Session.query("id","publisher_id")\
                .from_statement("SELECT id,publisher_id FROM harvest_source").all()
    for i,p in data:
        if p and len(p) == 5:
            old_id = int(p)

            ids = model.Session.query("id")\
                        .from_statement("select id from public.group where name='%s'" % publishers[old_id]).all()
            publisher_id = ids[0][0]
            print HARVEST_UPDATE % (publisher_id,i,)


def update_datasets():
    with_name = re.compile("^.*\[(\d+)\].*$")

    missing_initial = True
    package_ids = model.Session.query("id")\
                    .from_statement("SELECT id FROM package").all()
    package_ids = [p[0] for p in package_ids]
    for pid in package_ids:
#        if pid == '2b1370f3-694f-44e1-a07d-413361fec7c3':
#            from pdb import set_trace;
#            set_trace()
        provider = ""
        via = model.Session.query("id","value")\
                    .from_statement(DATASET_EXTRA_QUERY_VIA).params(package_id=pid).all()

        by = model.Session.query("id","value")\
                   .from_statement(DATASET_EXTRA_QUERY_BY).params(package_id=pid).all()

        via_value = via[0][1].strip("\"' ") if via else None
        by_value = by[0][1].strip("\"' ") if by else None
        if not via_value:
            if by_value:
                value = by_value
        else:
            value = via_value
            # We have a value but we should check against the BY query
            if via_value != by_value:
                if '[' in by_value:
                    provider = by_value[:by_value.index('[')].strip("\"' ")
                else:
                    provider = by_value


        # Use the with_name regex to strip out the number from something
        # of the format "Name of the publisher [extra_id]"
        if value:
            try:
                g = with_name.match(str(value))
                if g:
                    value = g.groups(0)[0]
            except:
                print value
                raise
        # We want to use ints for the lookup, just because
        value = int(value or 0)

        # We don't handle unknown publishers but these should not exist as
        # we are looking from a shared datasource (i.e. publishers published
        # from same list).
        if not value or not value in publishers:
            log_missing_data(value, via_value or by_value, pid, first=missing_initial)
            missing_initial = False
            continue

        member_id          = unicode(uuid.uuid4())
        member_revision_id = unicode(uuid.uuid4())
        revision_id        = unicode(uuid.uuid4())
        provider_id        = unicode(uuid.uuid4())

        # We could optimise here, but seeing as the script currently runs adequately fast
        # we won't bother with caching the name->id lookup
        ids = model.Session.query("id")\
                    .from_statement("select id from public.group where name='%s'" % publishers[value]).all()
        publisher_id = ids[0][0]

        memberq      = MEMBER_QUERY.strip() % \
                        (member_id, pid, publisher_id, revision_id)
        member_rev_q = MEMBER_REVISION_QUERY.strip() % \
                        (member_id, pid, publisher_id, revision_id, member_id)
        revision_q   = REVISION_QUERY.strip() % (revision_id,)
        cleanup_q    = DATASET_EXTRA_CLEANUP.strip() % (publisher_id,)

        print revision_q
        print memberq
        print member_rev_q
        print cleanup_q
        if provider:
            print PROVIDER_INSERT % (provider_id, pid, provider)
        print ''



HARVEST_UPDATE = "UPDATE public.harvest_source SET publisher_id='%s' WHERE id='%s';"
PROVIDER_INSERT = """
INSERT INTO public.package_extra(id, package_id,key, value, state)
    VALUES ('%s', '%s', 'provider', '%s', 'active');
"""

MEMBER_QUERY = """
INSERT INTO public.member(id, table_id,group_id, state,revision_id, table_name, capacity)
    VALUES ('%s', '%s', '%s', 'active', '%s', 'package', 'member');
"""
MEMBER_REVISION_QUERY = """
INSERT INTO public.member_revision(id, table_id, group_id, state, revision_id, table_name,
                                      capacity, revision_timestamp, current, continuity_id)
    VALUES ('%s', '%s', '%s', 'active', '%s', 'package', 'member',
            '2012-02-17',  true, '%s');
"""
REVISION_QUERY = """
INSERT INTO public.revision(id, timestamp, author, message, state, approved_timestamp)
    VALUES ('%s','2012-02-17', 'admin', 'Migration task', 'active',
            '2012-02-17');
"""

DATASET_EXTRA_QUERY_VIA = \
    "SELECT id,package_id, value FROM package_extra WHERE key='published_via' AND package_id=:package_id"
DATASET_EXTRA_QUERY_BY = \
    "SELECT id, value FROM package_extra WHERE key='published_by' AND package_id=:package_id"
DATASET_EXTRA_CLEANUP = \
    "DELETE FROM package_extra WHERE (key='published_via' OR key='published_by') AND package_id='%s';"



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
