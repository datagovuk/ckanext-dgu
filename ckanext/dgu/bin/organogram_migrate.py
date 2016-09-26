'''Migrates organogram data from TSO to CKAN. Is idempotent.
'''
import argparse
import unicodecsv
import datetime
import re
import os
import sys
import traceback
import shutil
import logging

# pip install 'ProgressBar==2.3'
from progressbar import ProgressBar, Percentage, Bar, ETA

import common
from running_stats import Stats

from ckanext.dgu.model.organogram import Organogram
# etl_to_csv is copied in from the organograms repo
from ckanext.dgu.bin.organograms_etl_to_csv import load_xls_and_get_errors, save_csvs

logging.basicConfig()
unicodecsv.field_size_limit(sys.maxsize)

args = None

def migrate(config_ini):
    repos_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', '..', '..'))
    in_filename = os.path.join(repos_path, 'organograms', 'tso_combined.csv')
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        tso_combined = [row for row in csv_reader]

    in_filename = os.path.join(repos_path, 'organograms', 'uploads_report_with_private.csv')
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        uploads_by_xls_path = dict([(row['xls_path'], row)
                                    for row in csv_reader])

    common.load_config(config_ini)
    common.register_translator()
    from ckan import model
    #apikey = config['dgu.merge_datasets.apikey']
    #ckan = ckanapi.RemoteCKAN('https://data.gov.uk', apikey=apikey)
    #ckan = ckanapi.LocalCKAN()
    #results = ckan.action.package_search(q=options.search, fq='publisher:%s' % org_name, rows=100)

    dirs = (get_xls_filepath('').rstrip('/'), get_csv_filepath('').rstrip('/'))
    for dir_ in dirs:
        if not os.path.exists(dir_):
            print 'Creating dir %s' % dir_
            os.mkdir(dir_)

    stats = Stats()
    widgets = ['Organograms: ', Percentage(), ' ', Bar(), ' ', ETA()]
    progress = ProgressBar(widgets=widgets)
    for row in progress(tso_combined):
        try:
            graph = date_to_year_first(row['graph'])
            if args.body and args.body != row['body_title']:
                continue
            if args.graph and args.graph != graph:
                continue

            org = model.Session.query(model.Group) \
                .filter_by(title=row['body_title']) \
                .first()
            if not org:
                print stats.add('Error: could not find org', row['body_title'])
                continue
            upload = uploads_by_xls_path[row['original_xls_filepath']] \
                if row['original_xls_filepath'] else None
            date = datetime.datetime.strptime(row['graph'], '%Y-%m-%d')
            user = upload['submitter_email'] if upload else '(extracted from legacy triplestore)'
            upload_date = \
                datetime.datetime(*map(int, re.split('[^\d]', row['upload_date'])[:-1])) \
                if row['upload_date'] else None
            action_date = \
                datetime.datetime(*map(int, re.split('[^\d]', row['publish_date'])[:-1])) \
                if row['publish_date'] else None
            organogram_dict = dict(
                publisher_id=org.id,
                date=date,
                #original_xls_filepath=row['original_xls_filepath'],
                upload_user=user,
                upload_date=upload_date,
                signoff_user=None,
                signoff_date=None,
                publish_user=None,
                publish_date=None,
                state=row['state'],
                )
            if row['state'] == 'uploaded':
                pass
            elif row['state'] == 'signed off':
                organogram_dict['signoff_user'] = user
                organogram_dict['signoff_date'] = action_date
            elif row['state'] == 'published':
                organogram_dict['signoff_user'] = user
                organogram_dict['signoff_date'] = None
                organogram_dict['publish_user'] = user
                organogram_dict['publish_date'] = action_date

            existing_organogram = Organogram.get(org.id, date)
            if existing_organogram:
                filepaths = (
                    existing_organogram.xls_filepath,
                    existing_organogram.csv_senior_filepath,
                    existing_organogram.csv_junior_filepath,
                    )
                for filepath in filepaths:
                    if os.path.exists(filepath):
                        os.remove(filepath)

            # Extract and Transform
            source_xls_filepath = full_path_source_data(row['xls_path'])
            try:
                senior_df, junior_df, errors, warnings, will_display = \
                    load_xls_and_get_errors(source_xls_filepath)
            except Exception:
                print stats.add('Error - etl exception', source_xls_filepath)
                traceback.print_exc()
                import pdb; pdb.set_trace()
            if senior_df is None or junior_df is None:
                stats.add('ETL error: %s' % ' / '.join(errors),
                          '"%s" %s' % (org.title, graph))
                continue

            # Save to CSV
            csv_rel_filepaths = []
            for senior_or_junior in ('senior', 'junior'):
                out_filename = '{org}-{graph}-{senior_or_junior}.csv'.format(
                    org=munge_org(org.title, separation_char='_'),
                    graph=graph.replace('/', '-'),
                    senior_or_junior=senior_or_junior)
                check_filename_is_unique(
                    get_csv_filepath(out_filename, relative=True),
                    'csv_%s_filepath' % senior_or_junior,
                    organogram_dict, stats)
                csv_rel_filepaths.append(get_csv_filepath(out_filename, relative=True))
            senior_csv_rel_filepath, junior_csv_rel_filepath = csv_rel_filepaths
            senior_csv_filepath, junior_csv_filepath = \
                [full_path(rel_path) for rel_path in csv_rel_filepaths]

            save_csvs(senior_csv_filepath, junior_csv_filepath,
                      senior_df, junior_df)
            organogram_dict['csv_senior_filepath'] = senior_csv_rel_filepath
            organogram_dict['csv_junior_filepath'] = junior_csv_rel_filepath

            # copy the XLS file into the organogram dir
            if row['original_xls_filepath']:
                xls_filename = munge_xls_path(row['original_xls_filepath'])
            else:
                xls_filename = 'from-triplestore-' + row['xls_path'].split('/')[-1]
            xls_rel_filepath = get_xls_filepath(xls_filename, relative=True)
            check_filename_is_unique(xls_rel_filepath, 'xls_filepath',
                                     organogram_dict, stats)
            xls_filepath = full_path(xls_rel_filepath)
            if os.path.exists(xls_filepath):
                os.remove(xls_filepath)
            shutil.copyfile(source_xls_filepath, xls_filepath)
            organogram_dict['xls_filepath'] = xls_rel_filepath

            # save to the database
            if existing_organogram:
                existing_organogram.update(**organogram_dict)
            else:
                organogram = Organogram(**organogram_dict)
                model.Session.add(organogram)
            model.Session.commit()
        except:
            print 'Exception with --body "%s" --graph %s' % \
                (row['body_title'], graph)
            traceback.print_exc()
            import pdb; pdb.set_trace()

        stats.add('Migrated', '"%s" %s' % (org.title, graph))
    try:
        print '\nMigrate:'
        print stats
    except:
        traceback.print_exc()
        import pdb; pdb.set_trace()

#     publisher_id = Column(types.UnicodeText, nullable=False, index=True)
#     date = Column(types.DateTime, nullable=False, index=True)  # i.e. version
#     original_xls_filepath = Column(types.UnicodeText, nullable=True, index=True)  # where it was stored on tso or the upload filename
#     xls_filepath = Column(types.UnicodeText, nullable=False, index=True)  # where we store it, relative to organogram dir
#     csv_senior_filepath = Column(types.UnicodeText, nullable=True) # where we store it, relative to organogram dir
#     csv_junior_filepath = Column(types.UnicodeText, nullable=True) # where we store it, relative to organogram dir

#     upload_user = Column(types.UnicodeText, nullable=False)  # user_id or string for legacy
#     upload_date = Column(types.DateTime, nullable=False, default=datetime.now)
#     signoff_user = Column(types.UnicodeText, nullable=True)
#     signoff_date = Column(types.DateTime, nullable=True)
#     publish_user = Column(types.UnicodeText, nullable=True)
#     publish_date = Column(types.DateTime, nullable=True)

#     state = Column(types.UnicodeText, nullable=False, index=True)

def check_filename_is_unique(relative_filepath, field, organogram_dict, stats):
    from ckan import model
    another_organogram_with_same_filename = model.Session.query(Organogram) \
        .filter(getattr(Organogram, field) == relative_filepath) \
        .filter(Organogram.publisher_id != organogram_dict['publisher_id']) \
        .filter(Organogram.date != organogram_dict['date']) \
        .first()
    if another_organogram_with_same_filename:
        print stats.add(
            'Error: Overwriting another organogram with the same xls filename',
            another_organogram_with_same_filename.xls_filepath)


def munge_org(name, separation_char='-'):
    '''Return the org name, suitable for a filename'''
    name = name.lower()
    # separators become dash/underscore
    name = re.sub('[ .:/&]', separation_char, name)
    # take out not-allowed characters
    name = re.sub('[^a-z0-9-_]', '', name)
    # remove doubles
    name = re.sub('-+', '-', name)
    name = re.sub('_+', '_', name)
    return name

def munge_xls_path(name):
    '''Make the XLS path bits suitable to be part of the saved filename,
    getting rid of the /data/ bit.
    /data/acas/2011-09-30/ACAS-SEPT-2011-TRANSPERANCYa.xls
    ->
    acas__2011-09-30__ACAS-SEPT-2011-TRANSPERANCYa
    '''
    parts = name.split('/')
    assert len(parts) == 5, name
    name = '%s__%s__%s' % (parts[2], parts[3], parts[4])
    name = '.'.join(name.split('.')[:-1])
    # separators become underscores
    name = re.sub('[ .:/&]', '-', name)
    # take out not-allowed characters
    name = re.sub('[^A-Za-z0-9-_]', '', name)
    # remove doubles
    name = re.sub('-+', '-', name)
    name = re.sub('_+', '_', name)
    return name

def date_to_year_first(date_day_first):
    return '-'.join(date_day_first.split('/')[::-1])

def get_csv_filepath(filename, relative=False):
    relative_filepath = os.path.join('csv', filename)
    if relative:
        return relative_filepath
    return full_path(relative_filepath)

def get_xls_filepath(filename, relative=False):
    relative_filepath = os.path.join('xls', filename)
    if relative:
        return relative_filepath
    return full_path(relative_filepath)

def full_path(relative_filepath):
    from pylons import config
    organogram_dir = config['dgu.organogram_dir']
    return os.path.join(organogram_dir, relative_filepath)

def full_path_source_data(relative_filepath):
    source_dir = args.source_data_dir  # e.g. ../organograms
    return os.path.join(source_dir, relative_filepath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ckan_ini', help='$CKAN_INI')
    parser.add_argument('source_data_dir', help='Path containing data/dgu/xls dir e.g. ../organograms')
    parser.add_argument('--check', action='store_true',
                        help='Check the XLS validates')
    parser.add_argument('--body')
    parser.add_argument('--graph')
    args = parser.parse_args()
    migrate(args.ckan_ini)