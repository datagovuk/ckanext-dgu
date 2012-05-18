import copy
import logging

import ckan.lib.cli
from ckan.lib.create_test_data import CreateTestData
from ckan import model        

log = logging.getLogger(__name__)

class DguCreateTestData(CreateTestData):
    _users = [
        {'name': 'sysadmin',
         'fullname': 'Test Sysadmin',
         'password': 'pass'},
        {'name': 'nhsadmin',
         'fullname': 'NHS Admin',
         'password': 'pass'},
        {'name': 'nhseditor',
         'fullname': 'NHS Editor',
         'password': 'pass'},
        {'name': 'user',
         'fullname': 'John Doe - a public user',
         'password': 'pass'},
        ]
    _publishers = [
        {'name': 'dept-health',
         'title': 'Department of Health',
         'contact-email': 'contact@doe.gov.uk'},
        {'name': 'nhs',
         'title': 'National Health Service',
         'contact-email': 'contact@nhs.gov.uk',
         'parent': 'dept-health'},
        {'name': 'barnsley-pct',
         'title': 'Barnsley Primary Care Trust',
         'contact-email': 'contact@barnsley.nhs.gov.uk',
         'parent': 'nhs'},
        {'name': 'newport-pct',
         'title': 'Newport Primary Care Trust',
         'contact-email': 'contact@newport.nhs.gov.uk',
         'parent': 'nhs'},
        {'name': 'ons',
         'title': 'Office for National Statistics',
         'contact-email': 'contact@ons.gov.uk'},
        {'name': 'cabinet-office',
         'title': 'Cabinet Office',
         'contact-email': 'contact@cabinet-office.gov.uk'},
        ]
    _roles = [('sysadmin', 'admin', 'system'),
              ]
    _user_publisher_memberships = [
        ('nhsadmin', 'admin', 'nhs'),
        ('nhseditor', 'editor', 'nhs'),
        ]
    _packages = [
        # Package edited on new form (June 2012)
        {'name': "directgov-cota",
         'title': "Directgov Article Ratings",
         'notes': "Ratings for all articles on the Directgov website.  One data file is available per day. Sets of files are organised by month on the download page",
         'license_id': 'uk-ogl',
         'tags': ["article", "cota", "directgov", "information", "ranking", "rating"],
         'groups': ['cabinet-office'],
         'extras': {
             'access_constraints': '',
             'contact-email': '',
             'contact-name': '',
             'contact-phone': '',
             'foi-email': '',
             'foi-name': '',
             'foi-phone': '',
             'geographic_coverage': "000000: ",
             'mandate': '',
             'temporal_coverage-to': "",
             'temporal_coverage-from': "",
             'temporal_granularity': "",
             'theme-primary': "Society",
             'theme-secondary': "",
             },
         'resources': [
             {'url': "http://innovate-apps.direct.gov.uk/cota/",
              'format': 'HTML',
              'description': "Directgov Article Ratings",
              },
             ]
         },
        # Package entered with Old Form (form from before June2012)
        {'name': 'cabinet-office-energy-use',
         'title': 'Cabinet Office 70 Whitehall energy use',
         'notes': """Cabinet Office head office energy use updated from on-site meters showing use, cost and carbon impact.""",
         'license_id': 'uk-ogl',
         'tags': ["cabinet-office", "consumption", "energy", "energy-consumption", "energy-use", "hq-building", "live-data-page", "real-time"],
         'groups': ['cabinet-office'],
         'extras': {
             'agency': "",
             'categories': "",
             'department': "Cabinet Office",
             'date_released': "2010-07-30",
             'date_updated': '2012-02-28',
             'date_update_future': '2013-02-28',
             'external_reference': "",
             'geographic_coverage': "000000: ",
             'geographic_granularity': "point",
             'national_statistic': "no",
             'openness_score_last_checked': "2011-06-06T14:22:24.001911",
             'openness_score': "3",
             'published_via': "",
             'precision': "",
             'published_by': "Cabinet Office [11407]",
             'temporal_coverage-to': "",
             'temporal_coverage-from': "",
             'temporal_granularity': "",
             'taxonomy_url': "",
             'update_frequency': "Real-time",
             },
         'resources': [
             {"hash": "",
              "description": "70 Whitehall energy data",
              "format": "CSV",
              "mimetype_inner": None,
              # NB Commenting out those that have Null values for date/int types as it is easiest
              #"webstore_last_updated": None,
              #"size": None,
              "mimetype": None,
              "cache_url": None,
              "name": None,
              "url": "http://data.carbonculture.net/orgs/cabinet-office/70-whitehall/reports/elec00.csv",
              #"cache_last_updated": None,
              "webstore_url": None,
              #"last_modified": None,
              "resource_type": None,
              },
             ]
           },
        # ONS package
        {'name': 'gdp_and_the_labour_market_',
         'title': 'GDP and the Labour Market',
         'notes': """Comparison of developments in GDP and the labour market in the latest quarter.

Source agency: Office for National Statistics

Designation: Supporting material

Language: English

Alternative title: GDP and Labour Market coherence""",
         'license_id': 'uk-ogl',
         'tags': ["economics-and-finance", "economy", "employment", "employment-jobs-and-careers", "gdp-labour-market-employment-unemployment-economy-growth", "labour-market", "national-accounts", "national-income-expenditure-and-output", "people-in-work", "uk-economy"],
         'groups': ['ons'],
         'extras': {
             'categories': "Economy",
             'date_released': '2012-01-25',
             'external_reference': 'ONSHUB',
             'geographic_granularity': "UK and GB",
             'geographic_coverage': '111100: United Kingdom (England, Scotland, Wales, Northern Ireland)',
             'import_source': "ONS-ons_data_7_days_to_2012-04-25",
             'national_statistic': 'yes',
             'precision': "",
             'published_by': "Office for National Statistics [11408]",
             'published_via': '',
             'series': 'GDP and the Labour Market',
             'temporal_coverage-from': "",
             'temporal_granularity': "",
             'update_frequency': "quarterly",
             },
         'resources': [
             {"hash": "",
              "description": "2011 Q4 - January GDP update",
              "format": "",
              "mimetype_inner": None,
              # NB Commenting out those that have Null values for date/int types as it is easiest
              #"webstore_last_updated": None,
              #"size": None,
              "mimetype": None,
              "cache_url": None,
              "name": None,
              "url": "http://www.ons.gov.uk/ons/dcp19975_250599.xml",
              #"cache_last_updated": None,
              "webstore_url": None,
              #"last_modified": None,
              "resource_type": None,
              "extras": {
                  "hub-id": "77-250599",
                  },
              },
             {"hash": "",
              "description": "2011 Q4 - February Labour Market update",
              "format": "",
              "mimetype_inner": None,
              #"webstore_last_updated": None,
              #"size": None,
              "mimetype": None,
              "cache_url": None,
              "name": None,
              "url": "http://www.ons.gov.uk/ons/dcp19975_250603.xml",
              #"cache_last_updated": None,
              "webstore_url": None,
              #"last_modified": None,
              "resource_type": None,
              "extras": {
                  "hub-id": "77-250603",
                  },
              }
             ]
           },
        # UKLP dataset
        {'name': 'cadastreni-wms',
         'title': "CadastreNI (WMS)",
         'notes': "WMS",
         'license_id': None,
         'extras': {
             'bbox-east-long': "-5.40566902640608",
             'temporal_coverage-from': "[]",
             'resource-type': "service",
             'bbox-north-lat': "55.3184340550243",
             'coupled-resource': '[{"href": ["http://webservices.spatialni.gov.uk/arcgis/services/LPS/CadastreNI/MapServer/WMSServer"], "uuid": ["http://webservices.spatialni.gov.uk/arcgis/services/LPS/CadastreNI/MapServer/WMSServer"], "title": []}]',
             'guid': "5b850805-8c62-4521-9dec-a448dfabe7f3",
             'bbox-south-lat': "54.0295252443606",
             'temporal_coverage-to': "[]",
             'spatial-reference-system': "CRS:84",
             'spatial': '{"type":"Polygon","coordinates":[[[-5.40566902640608, 54.0295252443606],[-5.40566902640608, 55.3184340550243], [-8.17548890898914, 55.3184340550243], [-8.17548890898914, 54.0295252443606], [-5.40566902640608, 54.0295252443606]]]}',
             'access_constraints': '["no limitations"]',
             'contact-email': "suzanne.mclaughlin@dfpni.gov.uk",
             'bbox-west-long': "-8.17548890898914",
             'metadata-date': "2012-02-02",
             'dataset-reference-date': '[{"type": "creation", "value": "2007-05-01"}]',
             'published_by': 33627,
             'frequency-of-update': "",
             'licence': "[]",
             'harvest_object_id': "55189d47-b1ea-4266-96b1-68cd10a3d0fd",
             'responsible-party': "LPS (pointOfContact)",
             'INSPIRE': "True",
             'spatial-data-service-type': "view",
             'metadata-language': "eng"             
            },
         'resources': [
             {'hash': "",
              'description': "Resource locator",
              'format': "WMS",
              'mimetype_inner': None,
              #'webstore_last_updated': None,
              #'size': None,
              'mimetype': None,
              'cache_url': None,
              'name': "",
              'url': "http://webservices.spatialni.gov.uk/arcgis/services/LPS/CadastreNI/MapServer/WMSServer",
              #'cache_last_updated': None,
              'webstore_url': None,
              #'last_modified': None,
              'resource_type': None,
              'extras': {
                  'verified_date': "2012-02-23T15:59:18.736889",
                  'verified': "True",
                  'resource_locator_function': "",
                  'resource_locator_protocol': "",
                  'ckan_recommended_wms_preview': "True",
                  }
              },
             ]
         },
        
         ]     
             

    @classmethod
    def create_publishers(cls, publishers):
        '''Creates publisher objects (special groups).
        The publisher['parent'] property should be set to the name of the
        parent publisher, if there is one.
        '''
        # Create all the groups
        groups = []
        for publisher in publishers:
            group = copy.deepcopy(publisher)
            group['type'] = 'publisher'
            group['parent'] = None
            groups.append(group)
        cls.create_groups(groups, auth_profile='publisher')

        # Add in the hierarchy (similar to bin/import_publishers.py)
        model.repo.new_revision()
        for publisher in publishers:
            g = model.Group.get(publisher['name'])
            parent_name = publisher.get('parent')
            if parent_name:
                parent = model.Group.get(parent_name)
                if model.Session.query(model.Member).\
                       filter(model.Member.group==parent and \
                              model.Member.table_id==g.id).count() == 0:
                    log.debug('Made "%s" parent of "%s"', parent_name, publisher['name'])
                    m = model.Member(group=parent, table_id=g.id, table_name='group')                 
                    model.Session.add(m)
                else:
                    log.debug('No need to make "%s" parent of "%s"', parent_name, publisher['name'])                    
        model.Session.commit()        

    @classmethod
    def create_user_publisher_memberships(cls, memberships):
        from ckan import model
        model.repo.new_revision()
        for user_name, capacity, publisher_name in memberships:
            user = model.User.by_name(user_name)
            assert user
            publisher = model.Group.get(publisher_name)
            assert publisher, publisher_name
            assert capacity in ('admin', 'editor')
            existing_membership = model.Session.query(model.Member)\
                                  .filter_by(table_name='user')\
                                  .filter_by(table_id=user.id)\
                                  .filter_by(group_id=publisher.id)
            if existing_membership.count() == 0:
                m = model.Member(group_id=publisher.id, table_id=user.id,
                                 table_name='user', capacity=capacity)
                model.Session.add(m)
                log.debug('Made: "%s" %s for "%s"', user_name, capacity, publisher_name)                    
            else:
                log.debug('No need to make "%s" %s for "%s"', user_name, capacity, publisher_name)                    
                
        model.Session.commit()        

    @classmethod
    def create_roles(cls, roles):
        '''This is just a basic version for CKAN 1.7.1 - the full version
        will be in CKAN 1.8.'''
        for subj, role, obj in roles:
            assert role, obj == ('admin', 'system')

            subj = model.User.by_name(unicode(subj))
            model.add_user_to_role(subj, model.Role.ADMIN, model.System())
            
        model.repo.commit_and_remove()

    @classmethod
    def create_dgu_test_data(cls):
        ckan.lib.activity.logger.disabled = 1
        cls.create_users(cls._users)
        cls.create_publishers(cls._publishers)
        cls.create_roles(cls._roles)
        cls.create_user_publisher_memberships(cls._user_publisher_memberships)
        cls.create_arbitrary(cls._packages)
 
    @classmethod
    def ons_package(cls):
        return model.Package.by_name(u'gdp_and_the_labour_market_')

    @classmethod
    def old_form_package(cls):
        return model.Package.by_name(u'cabinet-office-energy-use')

    @classmethod
    def form_package(cls):
        return model.Package.by_name(u'directgov-cota')
