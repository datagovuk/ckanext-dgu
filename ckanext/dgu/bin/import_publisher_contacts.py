'''
Imports the DGU Publisher hierarchy from a manually assembled list of department contacts.
     This is a CSV file with columns: expected_columns (see below)
'''

import os
import logging
import sys
from sqlalchemy import engine_from_config, or_
import csv
from pylons import config
from nose.tools import assert_equal
from webhelpers.text import truncate

expected_columns = ('Department', 'Name', 'E-mail', 'Main dept contact', 'Type', 'FOI Contact', 'Transparency Contact')

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command(config_ini, contacts_csv):
    config_ini_filepath = os.path.abspath(config_ini)
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    logging.config.fileConfig(config_ini_filepath)
    log = logging.getLogger(os.path.basename(__file__))
    global global_log
    global_log = log

    from ckan import model
    model.init_model(engine)

    import_contacts()
    report()

def import_contacts():
    from ckan import model
    from ckan.lib.munge import munge_title_to_name

    # Collate all the publisher abbreviations
    log = global_log
    log.info('Collating publisher abbreviations')
    publisher_abbreviations = {} # {abbrev:name}
    publishers_with_no_abbreviation = []
    for group in model.Group.all(group_type='organization'):
        abbrev = group.extras.get('abbreviation') or ''
        abbrev = abbrev.strip().lower()
        if abbrev:
            publisher_abbreviations[abbrev] = group.name
        else:
            publishers_with_no_abbreviation.append(group.name)
    log.info('Publishers abbreviations: %i with, %i without', len(publisher_abbreviations), len(publishers_with_no_abbreviation))

    # Go through the CSV and edit Groups
    model.repo.new_revision()
    with open(contacts_csv, 'rU') as contacts_csv_f:
        reader = csv.reader(contacts_csv_f)
        title = reader.next() #ignore
        headers = reader.next()
        assert_equal(tuple(headers), expected_columns)
        for row in reader:
            row = dict(zip(expected_columns, row))

            publisher = row['Department'].strip()
            if not publisher:
                warn('Ignoring row without publisher: %r', row)
                continue

            if publisher.lower() in publisher_abbreviations:
                g = model.Group.get(publisher_abbreviations[publisher.lower()])
            else:
                q = model.Group.all('organization').filter(or_((model.Group.name==publisher),
                                                            (model.Group.title==publisher)))
                if q.count() == 0:
                    warn('Cannot find publisher: %r', publisher)
                    continue
                elif q.count() > 1:
                    warn('Multiple matches for publisher: %r', publisher)
                    continue
                else:
                    g = q.one()

            model.repo.new_revision()
            edited = False
            if '*' in row['Main dept contact']:
                if row['Type'].strip() not in ('Practitioner', 'Both', 'Sub-Practitioner'):
                    warn('Surprised to see that the main dept contact %r has role %r', row['E-mail'], row['Type'])
                g.extras['contact-email'] = row['Transparency Contact'] or row['E-mail']
                log.info('%s has contact %r', g.name, g.extras['contact-email'])
                edited = True
            else:
                log.info('Ignoring non-asterisked contact: %r', (row['Department'], row['Name']))
            if row.get('FOI Contact').strip():
                g.extras['foi-email'] = row['FOI Contact'].strip()
                edited = True
                log.info('%s has FOI email %r', g.name, g.extras['foi-email'])
            model.Session.commit()
            title_and_abbreviation = '%s (%s)' % (g.title, row['Department']) if row['Department'] else g.title
            if edited:
                log.info('Edited publisher contact: %s', title_and_abbreviation)

    log.info('Processed rows: %i', reader.line_num)
    log.info('Warnings: %r', warnings)

def report():
    # report on top level publishers
    from ckan import model
    log = global_log
    log.info('Summary of top level publishers:')
    publishers = without_contact = without_foi = 0
    for publisher in model.Group.all('organization'):
        parent_groups = publisher.get_groups('organization')
        if parent_groups:
            continue
        group_extras = publisher.extras
        contact_details = group_extras['contact-email'] or group_extras['contact-phone']
        foi_details = group_extras['foi-email'] or group_extras['foi-phone']
        print '%s: Contact: %s Foi: %s' % (publisher.title,
                                           truncate(contact_details, 15) or 'NONE',
                                           truncate(foi_details, 15) or 'NONE')
        publishers += 1
        without_contact += 1 if not contact_details else 0
        without_foi += 1 if not foi_details else 0
    print 'Total top level publishers: %i' % publishers
    print 'Total without contact details: %i' % without_contact
    print 'Total without FOI details: %i' % without_foi


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

    python import_publishers.py <CKAN config ini filepath> <Contacts CSV filepath>
    """

if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
        sys.exit(0)
    cmd, config_ini, contacts_csv = sys.argv
    command(config_ini, contacts_csv)
