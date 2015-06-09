'''
Adds schema to datasets in the LGA Incentive Scheme CSV
'''

import common
import re
from optparse import OptionParser
import csv
import codecs
import os
from collections import namedtuple
import json

from running_stats import Stats


dataset_name_corrections = {
    'waverley-public-conveniences': 'waverley-borough-council-public-conveniences',
    'public-conveniences': 'public-conveniences2',
    }

Schema = namedtuple('Schema', ('lga_name', 'dgu_schema_name', 'search_for'))
all_schemas = [
    Schema(lga_name='Toilets', dgu_schema_name='Public Toilets (for LGTC by LGA)',
           search_for=['toilet', 'public_toilets', 'public conveniences']),
    Schema(lga_name='Premises', dgu_schema_name='Premises Licences (for LGTC by LGA)',
           search_for=['premises licence', 'premises license', 'premises licensing', 'licensed premises', 'premiseslicences']),
    Schema(lga_name='Planning', dgu_schema_name='Planning Applications (for LGTC by LGA)',
           search_for=['planning applications']),
    Schema(lga_name='', dgu_schema_name=u'Spend over \xa3500 by local authority (Expenditure transactions exceeding \xa3500) (for LGTC by LGA)',
           search_for=['spend', 'expenditure', u'\xa3500']),
    Schema(lga_name='', dgu_schema_name='Procurement Information (Local authority contracts) (for LGTC by LGA)',
           search_for=['procurement', 'contracts']),
    Schema(lga_name='', dgu_schema_name='Land and building assets (for LGTC by LGA)',
           search_for=['land assets', 'building assets', 'land ownership', 'land assets', 'land and property assets', 'local authority land', 'Public Property and Land', 'land terrier', 'Council Registered Land', 'owned land', 'council land', 'land owned']),
    Schema(lga_name='', dgu_schema_name='Organisation structure (org chart / organogram for local authority) (for LGTC by LGA)',
           search_for=['org chart', 'organisation chart', 'organisation structure']),
    Schema(lga_name='', dgu_schema_name='Senior employees of a local authority (for LGTC by LGA)',
           search_for=['senior staff', 'senior employees', 'senior roles']),
    Schema(lga_name='', dgu_schema_name='Salary counts of senior employees of a local authority (for LGTC by LGA)',
           search_for=['salary counts', 'senior salaries']),
    Schema(lga_name='', dgu_schema_name='Counter fraud activity (for LGTC)',
           search_for=['counter fraud', 'fraud', 'fradulent activity']),
    Schema(lga_name='', dgu_schema_name='Pay multiples across an organisation (for LGTC)',
           search_for=['pay multiples']),
    Schema(lga_name='', dgu_schema_name='Trade union facility time (for LGTC)',
           search_for=['trade union', 'facility time']),
    ]
all_schemas_by_lga_name = dict((s.lga_name, s) for s in all_schemas)
all_schemas_by_dgu_name = dict((s.dgu_schema_name, s) for s in all_schemas)

# LGA org : DGU org
la_map = {
    'North Devon District Council': 'North Devon Council',
    'St Helens Metropolitan Borough Council': 'St Helens Council',
    'Eastbourne Council': 'Eastbourne Borough Council',
    'Kings Lynn and West Norfolk Borough Council': 'Borough Council of King\'s Lynn and West Norfolk',
    'Bradford Metropolitan District Council': 'City of Bradford Metropolitan District Council',
    'Trafford Metropolitan Borough Council': 'Trafford Council',
    'Basildon District Council': 'Basildon Borough Council',
    'London Borough of Westminster': 'Westminster City Council',
    'Milton Keynes': 'Milton Keynes Council',
    'Oldham Metropolitan Borough Council': 'Oldham Council',
    'Bath & North East Somerset Council': 'Bath and North East Somerset Council',
    'Newcastle-upon-Tyne City Council': 'Newcastle City Council',
    'Worthing District Council': 'Worthing Borough Council',
    'Harlow District Council': 'Harlow Council',
    'Barrow-in-Furness Borough Council': 'Barrow Borough Council',
    'Northumberland Council': 'Northumberland County Council',
    'Gateshead Metropolitan Borough Council': 'Gateshead Council',
    'York City Council': 'City of York Council',
    'Kirklees Metropolitan Borough Council': 'Kirklees Council',
    }
# DGU org : LGA org
#la_reverse_map = dict([(dgu, lga) for (lga, dgu) in la_map.items()])


class LaSchemas(object):
    @classmethod
    def command(cls, config_ini, options, submissions_csv_filepath):

        # Inventive CSV. Columns:
        # applicationnumber, applicationdate, jobrole, laname, officerauthorised, theme, responsedate, acceptancestatus, odicertificateurl, dguurl, inventoryurl, localcodes, dataseturl, schemaurl, guidanceurl, frequencyofpublishing, foinumberest, submissioncomplete, lastlaupdate, techreviewstatus, lasttechupdate, adminreviewstatus, paymentamount, closed, lastadminupdate, applicantnotes, administrationnotes, technicalnotes, lastupdated
        with open(submissions_csv_filepath, 'rb') as f:
            csv = UnicodeCsvReader(f, encoding='iso-8859-1')
            header = csv.next()
            header = [col_name.strip().lower().replace(' ', '_') for col_name in header]
            Submission = namedtuple('Submission', header)
            submissions = [Submission(*row) for row in csv]

        if config_ini:
            # this is only for when running from the command-line
            #print 'Loading CKAN config...'
            common.load_config(config_ini)
            common.register_translator()
            #print '...done'

        from ckan import model
        from ckan.plugins import toolkit
        from ckanext.dgu.lib import helpers as dgu_helpers
        from ckanext.dgu.model.schema_codelist import Schema

        # Match the organizations in the submissions
        lga_orgs_by_dgu_org_name = {}
        accepted_submission_dgu_orgs = set()
        for submission in submissions:
            la_title = la_map.get(submission.laname, submission.laname)
            org = model.Session.query(model.Group) \
                       .filter_by(title=la_title) \
                       .first()
            assert org, 'Submission org title not found: %r' % la_title
            lga_orgs_by_dgu_org_name[org.name] = submission.laname
            if submission.acceptancestatus == 'Accepted':
                accepted_submission_dgu_orgs.add(org.name)

        stats = Stats()
        stats_incentive = Stats()
        results = []

        if options.write:
            rev = model.repo.new_revision()
            rev.author = 'script-%s.py' % __file__

        # Iterate over organizations
        if options.dataset:
            dataset = toolkit.get_action('package_show')(data_dict={'id': options.dataset})
            org_names = [dataset['organization']['name']]
        elif options.organization:
            org_names = [options.organization]
        elif options.incentive_only:
            org_names = sorted(accepted_submission_dgu_orgs)
        else:
            org_names = dgu_helpers.all_la_org_names()
        #print '%s organizations' % len(org_names)
        for org_name in org_names:
            org_title = model.Group.by_name(org_name).title
            lga_org = lga_orgs_by_dgu_org_name.get(org_name)

            # Iterate over the schemas
            if options.schema:
                schemas = [all_schemas_by_lga_name.get(
                           options.schema,
                           all_schemas_by_dgu_name[options.schema])]
            elif options.incentive_only:
                schemas = [all_schemas_by_lga_name[submission.theme]
                           for submission in submissions
                           if submission.laname == lga_org
                           and submission.acceptancestatus == 'Accepted']
            else:
                schemas = all_schemas
            #print '%s schemas' % len(schemas)
            for schema in schemas:

                # Find the relevant incentive submission
                if lga_org:
                    for submission in submissions:
                        if submission.laname == lga_org and \
                                submission.theme == schema.lga_name:
                            break
                    else:
                        submission = None
                else:
                    submission = None

                result = dict(
                    org_name=org_name,
                    org_title=org_title,
                    org_name_lga=submission.laname if submission else '',
                    schema_dgu_title=schema.dgu_schema_name,
                    schema_lga=schema.lga_name,
                    lga_application_number=submission.applicationnumber if submission else '',
                    lga_application_acceptance_status=submission.acceptancestatus if submission else '',
                    dataset_names=[],
                    dataset_titles=[],
                    dataset_schema_applied=[],
                    )

                stat_id = '%s %s' % (org_name, schema.lga_name)
                if submission:
                    stat_id += ' %s' % submission.applicationnumber

                def add_datasets_to_results(datasets, result):
                    for dataset in datasets:
                        if dataset['name'] not in result['dataset_names']:
                            result['dataset_names'].append(dataset['name'])
                            result['dataset_titles'].append(dataset['title'])
                            schema_applied = True if schema.dgu_schema_name in \
                                [s['title'] for s in dataset.get('schema', [])] \
                                else False
                            result['dataset_schema_applied'].append(schema_applied)
                            if not schema_applied and options.write:
                                pkg = model.Package.get(dataset['name'])
                                schema_obj = Schema.by_title(schema.dgu_schema_name)
                                assert schema_obj
                                try:
                                    schema_ids = json.loads(pkg.extras.get('schema') or '[]')
                                except ValueError:
                                    log.error('Not valid JSON in schema field: %s %r',
                                              dataset['name'], pkg.extras.get('schema'))
                                    schema_ids = []
                                schema_ids.append(schema_obj.id)
                                pkg.extras['schema'] = json.dumps(schema_ids)

                # Already a schema?
                data_dict = {'fq': 'publisher:%s ' % org_name +
                                   'schema_multi:"%s"' % schema.dgu_schema_name}
                datasets = toolkit.get_action('package_search')(data_dict=data_dict)
                if datasets['count'] > 0:
                    add_datasets_to_results(datasets['results'], result)
                    stats.add('OK - Dataset with schema',
                              stat_id + ' %s' % ';'.join(result['dataset_names']))
                    found_schema = True
                else:
                    found_schema = False

                # Submission specifies DGU dataset
                if submission and submission.dguurl:
                    match = re.match('http://data.gov.uk/dataset/(.*)', submission.dguurl)
                    if match:
                        dataset_name = dataset_name_original = match.groups()[0]
                        # some have trailing /
                        dataset_name = dataset_name.strip('/')
                        # hampshire have a hash appended
                        if '#' in dataset_name:
                            dataset_name = dataset_name.split('#')[0]
                        # poole have a resource name appended
                        if '/resource' in dataset_name:
                            dataset_name = dataset_name.split('/resource')[0]
                        # manual corrections
                        if dataset_name in dataset_name_corrections:
                            dataset_name = dataset_name_corrections[dataset_name]
                        dataset = model.Package.by_name(dataset_name)
                        # salford ones added a '1'
                        if not dataset:
                            dataset = model.Package.by_name(dataset_name + '1')
                            if dataset:
                                dataset_name += '1'

                        if dataset and dataset.state == 'active':
                            dataset_dict = toolkit.get_action('package_show')(data_dict={'id': dataset.id})
                            add_datasets_to_results([dataset_dict], result)
                            if dataset_name != dataset_name_original:
                                stats_incentive.add('OK - DGU Dataset listed and with corrections it checks out',
                                          stat_id + ' %s' % dataset_name)
                            else:
                                stats_incentive.add('OK - DGU Dataset listed and it checks out',
                                          stat_id + ' %s' % dataset_name)
                        elif dataset:
                            stats_incentive.add('ERROR - DGU Dataset listed BUT it is deleted!',
                                            '%s %s' % (stat_id, submission.dguurl))
                        else:
                            stats_incentive.add('ERROR - DGU Dataset listed BUT it is not found',
                                            '%s %s' % (stat_id, submission.dguurl))
                    else:
                        stats_incentive.add('ERROR - DGU Dataset listed BUT the URL is not the correct format',
                                        '%s %s' % (stat_id, submission.dguurl))

                # Submission mentions dataset on LA site - maybe it is in DGU already?
                elif submission and submission.dataseturl:
                    datasets = model.Session.query(model.Package) \
                                    .join(model.ResourceGroup) \
                                    .join(model.Resource) \
                                    .filter(model.Resource.url==submission.dataseturl) \
                                    .filter(model.Package.state=='active') \
                                    .filter(model.Resource.state=='active') \
                                    .all()
                    dataset_dicts = [
                        toolkit.get_action('package_show')(data_dict={'id': dataset.id})
                        for dataset in datasets]
                    add_datasets_to_results(dataset_dicts, result)
                    if len(datasets) > 1:
                        stats_incentive.add('No DGU Dataset, but Dataset URL matches multiple DGU datasets',
                                            '%s %s' % (stat_id, datasets[0].name))
                    elif len(datasets) == 0:
                        stats_incentive.add('No DGU Dataset and Dataset URL not found on DGU',
                                            stat_id)
                    else:
                        stats_incentive.add('No DGU Dataset, but Dataset URL matches DGU dataset',
                                            '%s %s' % (stat_id, datasets[0].name))

                # Search for datasets in the catalogue
                datasets = cls.find_dataset_for_schema(schema=schema, org_name=org_name)
                if datasets is None:
                    if not found_schema:
                        stats.add('Search revealed none', stat_id)
                elif len(datasets) > 1:
                    add_datasets_to_results(datasets, result)
                    if not found_schema:
                        stats.add('Found datasets (multiple) in search', '%s %r' % (stat_id, [d['name'] for d in datasets]))
                elif datasets:
                    add_datasets_to_results(datasets, result)
                    if not found_schema:
                        stats.add('Found dataset in search', '%s %s' % (stat_id, datasets[0]['name']))
                else:
                    if not found_schema:
                        stats.add('No dataset for submission', stat_id)

                results.append(result)

        rows_with_datasets_count = \
            len([result for result in results
                 if any(result['dataset_schema_applied'])])
        rows_with_datasets_or_candidate_datasets_count = \
            len([result for result in results
                 if result['dataset_schema_applied']])

        if options.print_:
            print '\n Incentive stats\n' + stats_incentive.report()
            print '\n Overall stats\n' + stats.report()

        if options.write:
            print 'Writing'
            model.Session.commit()

        return {'table': results,
                'rows_with_datasets_count': rows_with_datasets_count,
                'rows_with_datasets_or_candidate_datasets_count': rows_with_datasets_or_candidate_datasets_count}

    @classmethod
    def find_dataset_for_schema(cls, schema, org_name):
        from ckan.plugins import toolkit

        datasets_for_org = toolkit.get_action('package_search')(
            data_dict={'fq': 'publisher:%s' % org_name})
        if datasets_for_org['count'] == 0:
            return None

        datasets = []
        dataset_names = set()
        for search_term in schema.search_for:
            data_dict = {'fq': 'title:"%s" ' % search_term +
                               'publisher:%s' % org_name}
            res = toolkit.get_action('package_search')(data_dict=data_dict)
            for dataset in res['results']:
                if dataset['name'] not in dataset_names:
                    datasets.append(dataset)
                    dataset_names.add(dataset['name'])

        return datasets


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeCsvReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

# Example submission
'''
{'acceptancestatus': u'Accepted',
 'administrationnotes': u'29/10/2014BACS payment process initiated as council has completed its obligations successfully\n21/10/2014Written to confirm data set is complete and acceptable. Reminded need of two versions of data needed - one with and one without georeferences. Forewarned that grant will be paid in a single payment once all themes as promised by the authority have been completed.',
 'adminreviewstatus': u'Accepted',
 'applicantnotes': u'07/10/2014we do not hold x&y refs in the planning db. we are looking to modify this in the comoing months and will add them to the submission then',
 'applicationdate': u'07/07/2014',
 'applicationnumber': u'36',
 'closed': u'True',
 'dataseturl': u'http://www.dover.gov.uk/Council--Democracy/Freedom-of-Information/CSV/Planning-Applications.csv',
 'dguurl': u'',
 'foinumberest': u'27',
 'frequencyofpublishing': u'Weekly',
 'guidanceurl': u'',
 'inventoryurl': u'',
 'jobrole': u'Support Supervisor',
 'laname': u'Dover District Council',
 'lastadminupdate': u'29/10/2014',
 'lastlaupdate': u'15/10/2014',
 'lasttechupdate': u'21/10/2014',
 'lastupdated': u'29/10/2014',
 'localcodes': u'',
 'odicertificateurl': u'https://certificates.theodi.org/datasets/2715/certificates/15121',
 'officerauthorised': u'True',
 'paymentamount': u'2000.0000',
 'responsedate': u'07/07/2014',
 'schemaurl': u'http://schemas.opendata.esd.org.uk/PlanningApplications',
 'submissioncomplete': u'True',
 'technicalnotes': u'21/10/2014Passed technical review.\n15/10/2014Not passed technical review, notes sent by email.\n13/10/2014Not passed technical review, notes sent by email.\n10/10/2014Not passed technical review, notes sent by email.\n08/10/2014Not passed technical review, notes sent by email.\n03/10/2014Not passed technical review, notes sent by email.',
 'techreviewstatus': u'Accepted',
 'theme': u'Planning'}
'''

usage = __doc__ + '''
Usage:
    python fix_themes.py <ckan.ini> <incentive.csv> [--write]'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes to the datasets")
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-o', '--organization', dest='organization')
    parser.add_option('-i', '--incentive-submissions-only', dest='incentive_only')
    parser.add_option('-s', '--schema', dest='schema')
    parser.add_option("-p",
                      action="store_false",
                      dest="print_",
                      default=True,
                      help="Instead of printing output, just log it")
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    csv_filepath = args[1]
    if not os.path.exists(csv_filepath):
        parser.error('CSV not found: %s', csv_filepath)
    # Convert utf8 in option inputs to unicode
    if options.schema:
        options.schema = options.schema.decode('utf8')
    LaSchemas.command(config_ini, options, csv_filepath)
