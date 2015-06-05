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

import requests
import requests_cache
requests_cache.install_cache('/tmp/dgu_cache', expire_after=60*60*24)

from running_stats import Stats


dataset_name_corrections = {
    'waverley-public-conveniences': 'waverley-borough-council-public-conveniences',
    'public-conveniences': 'public-conveniences2',
    }

Schema = namedtuple('Schema', ('lga_name', 'dgu_schema_name', 'search_for'))
schemas = [
    Schema(lga_name='Toilets', dgu_schema_name='Public Toilets (for LGTC by LGA)',
        search_for=['toilet', 'toilets', 'public_toilets', 'public conveniences']),
    Schema(lga_name='Premises', dgu_schema_name='Premises Licences (for LGTC by LGA)',
           search_for=['premises licence', 'premises license', 'premise licences', 'premises licences', 'premises licenses', 'premises licensing', 'licensed premises', 'premiseslicences']),
    Schema(lga_name='Planning', dgu_schema_name='Planning Applications (for LGTC by LGA)',
           search_for=['planning applications']),
    ]
schemas_by_lga_name = dict((s.lga_name, s) for s in schemas)

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


class SchemaApply(object):
    @classmethod
    def command(cls, config_ini, options, submissions_csv_filepath):

        print 'Reading submissions CSV...'
        with open(submissions_csv_filepath, 'rb') as f:
            csv = UnicodeCsvReader(f, encoding='iso-8859-1')
            header = csv.next()
            header = [col_name.strip().lower().replace(' ', '_') for col_name in header]
            Submission = namedtuple('Submission', header)
            submissions = [Submission(*row) for row in csv]
        print '...done'

        # Match the organizations in the submissions
        orgs_res = requests.get('http://data.gov.uk/api/action/organization_list?all_fields=1&include_groups=1')
        cls.orgs = orgs_res.json()['result']
        cls.orgs_by_title = dict([(org['title'], org) for org in cls.orgs])
        is_la_missing = False
        for submission in submissions:
            la_name = la_map.get(submission.laname, submission.laname)
            if la_name not in cls.orgs_by_title:
                print 'Missing: ', submission.applicationnumber, la_name
                is_la_missing = True
        assert not is_la_missing

        # Columns:
        # applicationnumber, applicationdate, jobrole, laname, officerauthorised, theme, responsedate, acceptancestatus, odicertificateurl, dguurl, inventoryurl, localcodes, dataseturl, schemaurl, guidanceurl, frequencyofpublishing, foinumberest, submissioncomplete, lastlaupdate, techreviewstatus, lasttechupdate, adminreviewstatus, paymentamount, closed, lastadminupdate, applicantnotes, administrationnotes, technicalnotes, lastupdated
        print 'Loading CKAN config...'
        common.load_config(config_ini)
        common.register_translator()
        print '...done'

        from ckan import model
        from ckan.plugins import toolkit

        # Iterate over organizations
        if options.dataset:
            dataset = toolkit.get_action('package_show')(data_dict={'id': options.dataset})
            org_names = [dataset['organization']['name']]
        elif options.organization:
            org_names = [options.organization]
        elif options.incentive_only:
            org_names = [cls.orgs_by_title[la_map.get(submission.laname, submission.laname)]['name']
                         for submission in submissions]
        else:
            org_names = [org['name'] for org in cls.orgs
                         if org['groups'] and
                         org['groups'][0]['name'] == 'local-authorities']
        #for org_name in org_names:

        # Check out the submissions

        stats = Stats()
        bad_submissions = []
        for submission in sorted(submissions, key=lambda s: int(s.applicationnumber)):
            # Example record:
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
            if submission.dguurl:
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
                        if dataset_name != dataset_name_original:
                            stats.add('OK - DGU Dataset listed and with corrections it checks out', dataset_name)
                        else:
                            stats.add('OK - DGU Dataset listed and it checks out', dataset_name)
                    elif dataset:
                        print stats.add('ERROR - DGU Dataset listed BUT it is deleted!',
                                '%s %s' % (submission.applicationnumber, submission.dguurl))
                        bad_submissions.append(submission)
                    else:
                        print stats.add('ERROR - DGU Dataset listed BUT it is not found',
                                '%s %s' % (submission.applicationnumber, submission.dguurl))
                        bad_submissions.append(submission)
                else:
                    print stats.add('ERROR - DGU Dataset listed BUT the URL is not the correct format',
                              '%s %s' % (submission.applicationnumber, submission.dguurl))
                    bad_submissions.append(submission)
            else:
                if submission.dataseturl:
                    datasets = model.Session.query(model.Package) \
                                    .join(model.ResourceGroup) \
                                    .join(model.Resource) \
                                    .filter(model.Resource.url==submission.dataseturl) \
                                    .filter(model.Package.state=='active') \
                                    .filter(model.Resource.state=='active') \
                                    .all()
                    if len(datasets) > 1:
                        print stats.add('ERROR - No DGU Dataset, but Dataset URL matches multiple DGU datasets',
                                  '%s %s' % (submission.applicationnumber, datasets[0].name))
                        bad_submissions.append(submission)
                    elif len(datasets) == 0:
                        stats.add('ERROR - No DGU Dataset, and no Dataset URL',
                                  '%s' % submission.applicationnumber)
                        bad_submissions.append(submission)
                    else:
                        dataset = datasets[0]
                        stats.add('OK - No DGU Dataset, but Dataset URL matches DGU dataset',
                                  '%s %s' % (submission.applicationnumber, dataset.name))

        print 'Submissions:'
        print stats.report()

        # Look for the missing ones in the submissions

        print '\nMissing submissions'
        print '-------------------'
        if options.write:
            rev = model.repo.new_revision()
            rev.author = 'script-%s.py' % __file__

        stats = Stats()
        for submission in bad_submissions:
            schema = schemas_by_lga_name[submission.theme]
            org = cls.orgs_by_title[la_map.get(submission.laname, submission.laname)]
            datasets = cls.find_dataset_for_schema(schema=schema, org=org)
            if datasets is None:
                print stats.add('No datasets at all for submission publisher', '%s %s' % (submission.applicationnumber, org['name']))
            elif len(datasets) > 1:
                print stats.add('Found multiple possible datasets for submission', '%s %s %r' % (submission.applicationnumber, submission.theme, [d['name'] for d in datasets]))
            elif datasets:
                dataset_name = datasets[0]['name']
                dataset = toolkit.get_action('package_show')(data_dict={'id': dataset_name})
                existing_schemas = [s['title'] for s in dataset.get('schema', [])]
                if schema.dgu_schema_name not in existing_schemas:
                    print stats.add('Found dataset for submission, SET schema', '%s %s %s' % (submission.applicationnumber, submission.theme, dataset_name))
                    dataset['schema'] = (dataset.get('schema') or []) + [schema.dgu_schema_name]
                else:
                    print stats.add('Found dataset for submission and schema already set', '%s %s %s' % (submission.applicationnumber, submission.theme, dataset_name))
            else:
                print stats.add('No dataset for submission', '%s %s' % (submission.applicationnumber, submission.theme))

        print 'Missing submissions:'
        print stats.report()

        if options.write:
            print 'Writing'
            model.Session.commit()

    @classmethod
    def find_dataset_for_schema(cls, schema, org):
        from ckan.plugins import toolkit

        datasets_for_org = toolkit.get_action('package_search')(
            data_dict={'fq': 'publisher:%s' % org['name']})
        if datasets_for_org['count'] == 0:
            return None

        datasets = []
        dataset_names = set()
        for search_term in schema.search_for:
            res = toolkit.get_action('package_search')(
                data_dict={
                    'fq': 'title:"%s" publisher:%s' % (schema.search_for, org['name'])})
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
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    csv_filepath = args[1]
    if not os.path.exists(csv_filepath):
        parser.error('CSV not found: %s', csv_filepath)
    SchemaApply.command(config_ini, options, csv_filepath)
