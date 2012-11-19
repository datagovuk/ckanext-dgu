# NB This is a test, but run by paster. Due to it importing paste/registry, this file can't
# live in the test directory.

from ckan.lib.cli import CkanCommand

class OnsPublisherTest(CkanCommand):
    '''
    Ensure we can translate all the values in the Source field into a publisher name.
    '''
    default_verbosity = 1
    group_name = 'ckanext-dgu'
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0
    max_args = 0
    
    def command(self):
        self._load_config()
        log = __import__('logging').getLogger(__name__)

        from ckanext.dgu.ons.importer import OnsImporter
        # sources pasted here from http://www.statistics.gov.uk/hub/statistics-producers/index.html
        sources = '''
Agri-Food and Biosciences Institute
Agriculture and Rural Development (Northern Ireland)
Business, Innovation and Skills
Cabinet Office
Child Maintenance and Enforcement Commission
Communities and Local Government
Culture, Media and Sport
Defence
Education
Education (Northern Ireland)
Employment and Learning (Northern Ireland)
Energy and Climate Change
Enterprise, Trade and Investment (Northern Ireland)
Environment (Northern Ireland)
Environment, Food and Rural Affairs
Food Standards Agency
Forestry Commission
HM Revenue and Customs
HM Treasury
Health
Health and Safety Executive
Health and Social Care Information Centre
Health Protection Agency
Health, Social Service and Public Safety (Northern Ireland)
Home Office
ISD Scotland (part of NHS National Services Scotland)
International Development
Justice
Justice (Northern Ireland)
Marine Management Organisation
National Records of Scotland
National Treatment Agency
Northern Ireland Statistics and Research Agency
Office for National Statistics
Office for Rail Regulation
Office for Standards in Education, Children\'s Services and Skills
Office of Qualifications and Examinations Regulation
Office of the First and Deputy First Minister
Passenger Focus
Police Service of Northern Ireland (PSNI)
Regional Development (Northern Ireland)
Scottish Government
Social Development (Northern Ireland)
Transport
Welsh Government
Work and Pensions
Civil Aviation Authority
Higher Education Statistics Agency
Eurostat
'''
        for source in sources:
            publisher = OnsImporter._source_to_publisher(source)
            assert publisher, source
        import pdb; pdb.set_trace()
        log.info('Completed successfully for %i sources', len(sources))
