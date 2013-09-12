'''
Uses a CSV export from DGU Drupal to determine which datasets are owned by
which publishers.

Iterates through all of the published_via extras for packages and then if it
is empty tries the published_by for that package.  Assuming we find something we
lookup the ID of the publisher (using the CSV instead of trusting the name) and
associate them.

This script produces SQL that needs to be run on the DGU/CKAN database.

It logs to publisher_datasets_assoc.log.

To create nodepublishermap.csv:
mysql -uroot dgu -e "
select nid, title from node where type='organization'
ORDER BY 'nid'
LIMIT 100000
INTO OUTFILE '/tmp/nodepublishermap.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '\"'
LINES TERMINATED BY '\n';"

To create ???:
mysql -uroot dgu -e "
SELECT
  distinct
  DI.ckan_id as 'dataset_id',
  (SELECT title FROM node_revisions
  AS rr
  WHERE rr.nid = K.field_publisher_nid ) AS 'publisher_title'
FROM content_type_ckan_package as K
INNER JOIN ckan_package as DI ON DI.nid = K.nid
ORDER BY 'publisher_title'
LIMIT 100000
INTO OUTFILE '/tmp/dunno.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '\"'
LINES TERMINATED BY '\n';"
'''


import os
import logging
import sys
import csv
import re
import uuid
from sqlalchemy import engine_from_config
from pylons import config, translator
from paste.registry import Registry

log = logging.getLogger(__name__)
publishers = {} # nid:publisher_name (munged)

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command(config_ini, nodepublisher_csv):
    config_ini_filepath = os.path.abspath(config_ini)
    load_config(config_ini_filepath)
    engine = engine_from_config(config,'sqlalchemy.')

    from ckan import model
    from ckan.lib.munge import munge_title_to_name

    logging.config.fileConfig(config_ini_filepath)
    log = logging.getLogger(os.path.basename(__file__))
    global global_log
    global_log = log

    model.init_model(engine)

    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from ckan.lib.cli import MockTranslator
    registry=Registry()
    registry.prepare()
    translator_obj=MockTranslator()
    registry.register(translator, translator_obj)

    model.repo.new_revision()

    log.info('Reading %s', nodepublisher_csv)
    with open(nodepublisher_csv, 'rU') as f:
        reader = csv.reader( f)
        for row in reader:
            nid, title = row
            publishers[ int(nid) ] = munge_title_to_name(title)
    # Mappings where we are getting rid of duplicate publishers
    publishers[16268] = publishers[11408] # UKSA -> ONS
    publishers[11606] = publishers[11408] # ONS
    publishers[20054] = publishers[16248] # Met Office
    publishers[33036] = publishers[15255] # Windsor & Maidenhead
    publishers[32619] = publishers[33245] # Monmouthshire
    publishers[12662] = publishers[11567] # NHS

    update_datasets()
    generate_harvest_publishers()

    log.info('Warnings: %r', warnings)

def generate_harvest_publishers():
    '''Generates SQL that converts the harvest_source.publisher_id from the
    Drupal node ID to CKAN publisher ID.'''
    from ckan import model
    data = model.Session.query("id","publisher_id")\
                .from_statement("SELECT id,publisher_id FROM harvest_source").all()
    for i,p in data:
        if p and len(p) == 5:
            old_id = int(p)

            if old_id in publishers:
                pub_name = publishers[old_id]
                publisher = model.Group.by_name(pub_name)
                if not publisher:
                    warn('Could not find publisher named %r. Cannot updating harvested records for that publisher.', pub_name)
                    continue
                #ids = model.Session.query("id")\
                #            .from_statement("select id from public.group where name='%s'" % publishers[old_id]).all()
                #publisher_id = ids[0][0]
                publisher_id = publisher.id
                print HARVEST_UPDATE % (publisher_id,i,)


def update_datasets():
    '''Generates SQL that makes every package a member of the appropriate
    group (publisher). It uses publisher_via and published_by to determine
    the group. If a package has both fields, then it is a member of
    published_via group, and published_by value becomes 'provider' extra.
    Any packages with neither values are logged.'''
    from ckan import model
    publisher_name_and_id_regex = re.compile("^(.*)\s\[(\d+)\].*$")
    publisher_id_regex = re.compile("^(\d+)$")

    package_ids = model.Session.query("id")\
                    .from_statement("SELECT id FROM package").all()
    package_ids = [p[0] for p in package_ids]
    for pkg in model.Session.query(model.Package):
        pid = pkg.id
        pkg_str = pkg.name
        if pkg.state != 'active':
            pkg_str += ' (%s)' % pkg.state
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
                if pkg.state == 'active':
                    warn('Dataset %s has no published_by/via - skipping.', pkg_str)
                else:
                    log.info('Dataset %s has no published_by/via - skipping.', pkg_str)
                continue
        else:
            value = via_value
            # We have a value but we should check against the BY query
            if via_value != by_value:
                if '[' in by_value:
                    provider = by_value[:by_value.index('[')].strip("\"' ")
                else:
                    provider = by_value

                provider = provider.replace("'", "\\'")

        # Use the publisher_name_and_id_regex to extract the publisher name and node_id from
        # value, which has format "Name of the publisher [node_id]"
        group_match = publisher_name_and_id_regex.match(str(value))
        if group_match:
            publisher_name, publisher_node_id = group_match.groups(0)
            publisher_node_id = int(publisher_node_id)
        else:
            group_match = publisher_id_regex.match(str(value))
            if group_match:
                publisher_name = None
                publisher_node_id = int(group_match.groups(0)[0])
            else:
                warn('Could not extract id from the publisher name: %r. Skipping package %s', value, pkg_str)
                continue

        # Lookup publisher object
        if publisher_name:
            publisher_q = model.Group.all('organization').filter_by(title=publisher_name)
        else:
            publisher_q = None
        if not publisher_q or publisher_q.count() == 0:
            # alternatively search by node_id mapping
            pub_name = publishers.get(publisher_node_id)
            if not pub_name:
                warn('Could not find publisher for node ID %r. Skipping package=%s published_by=%r published_via=%r',
                     publisher_node_id, pkg_str, by_value, via_value)
                continue
            publisher_q = model.Group.all('organization').filter_by(name=pub_name)
        if publisher_q.count() == 1:
            publisher = publisher_q.one()
        elif publisher_q.count() == 0:
            warn('Could not find publisher %r. Skipping package=%s published_by=%r published_via=%r',
                 publisher_name, pkg_str, by_value, via_value)
            continue
        elif publisher_q.count() > 1:
            warn('Multiple matches for publisher %r: %r. package=%s published_by=%r published_via=%r',
                 publisher_name, [(pub.id, pub.title) for pub in publisher_q.all()],
                 pkg_str, by_value, via_value)
            continue
        publisher_id = publisher.id

        member_id          = unicode(uuid.uuid4())
        member_revision_id = unicode(uuid.uuid4())
        revision_id        = unicode(uuid.uuid4())
        provider_id        = unicode(uuid.uuid4())

        log.info('Adding dataset %r to publisher %r',
                 model.Package.get(pid).name, publisher_name)

        membership_q = model.Session.query(model.Member).filter_by(table_id=pid,
                                                                 capacity='public',
                                                                 group_id=publisher_id)
        if membership_q.count():
            log.warn('Membership already added')
            continue

        member_q     = MEMBER_QUERY.strip() % \
                       (member_id, pid, publisher_id, revision_id)
        member_rev_q = MEMBER_REVISION_QUERY.strip() % \
                        (member_revision_id, pid, publisher_id, revision_id, member_id)
        revision_q   = REVISION_QUERY.strip() % (revision_id,)

        print revision_q
        print member_q
        print member_rev_q
        if provider:
            p = model.PackageExtra(id=unicode(uuid.uuid4()), package_id=pid,
                                   key='provider', value=provider)
            model.Session.add(p)
            model.Session.commit()
        print ''

warnings = []
global_log = None
def warn(msg, *params):
    global warnings
    warnings.append(msg % params)
    global_log.warn(msg, *params)

# Not currently deleting extras as it means this import cannot be run again
# and if we do it after we've generated the SQL it takes an excessively long
# time to clean up the revisions etc.
#    model.Session.query(model.PackageExtraRevision).\
#        filter(model.PackageExtraRevision.key == 'published_by' or
#               model.PackageExtraRevision.key == 'published_via').\
#        delete(synchronize_session=False)

#    model.Session.query(model.PackageExtra).\
#        filter(model.PackageExtra.key == 'published_by' or
#               model.PackageExtra.key == 'published_via').\
#        delete(synchronize_session=False)

HARVEST_UPDATE = "UPDATE public.harvest_source SET publisher_id='%s' WHERE id='%s';"

MEMBER_QUERY = """
INSERT INTO public.member(id, table_id,group_id, state,   revision_id, table_name, capacity)
                 VALUES ('%s', '%s',   '%s',    'active', '%s',        'package',  'public');
"""
MEMBER_REVISION_QUERY = """
INSERT INTO public.member_revision(id, table_id, group_id, state, revision_id, table_name,
                                      capacity, revision_timestamp, current, continuity_id, expired_timestamp)
    VALUES ('%s', '%s', '%s', 'active', '%s', 'package', 'public',
            '2012-02-17',  true, '%s', '9999-12-31');
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
    cmd, config_ini, nodepublisher_csv = sys.argv
    command(config_ini, nodepublisher_csv)
