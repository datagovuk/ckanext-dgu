import copy
import logging
import datetime

import ckan.lib.cli
from ckan.lib.create_test_data import CreateTestData
from ckan import model

log = logging.getLogger(__name__)

class DguCreateTestData(CreateTestData):
    _users = [
        {'name': 'sysadmin',
         'fullname': 'Test Sysadmin',
         'password': 'pass',
         'sysadmin': True},
        {'name': 'nhsadmin',
         'fullname': 'NHS Admin',
         'password': 'pass',
         'email': 'admin@nhs.gov.uk'},
        {'name': 'nhseditor',
         'fullname': 'NHS Editor',
         'password': 'pass'},
        {'name': 'user_d101',
         'fullname': 'NHS Editor imported from Drupal',
         'password': 'pass'},
        {'name': 'user',
         'fullname': 'John Doe - a public user',
         'password': 'pass'},
        {'name': 'user_d102',
         'fullname': 'John Doe - a public user',
         'password': 'pass'},
        {'name': 'dh_admin',
         'fullname': 'Dept Health Admin',
         'password': 'pass',
         'email': 'dohemail@localhost.local'},
        {'name': 'co_admin',
         'fullname': 'Cabinet Office Admin',
         'password': 'pass'},
        {'name': 'co_editor',
         'fullname': 'Cabinet Office Editor',
         'password': 'pass'},
        {'name': 'barnsley_editor',
         'fullname': 'Barnsley PCT Editor',
         'password': 'pass'},
        {'name': 'barnsley_admin',
         'fullname': 'Barnsley PCT Admin',
         'password': 'pass'},
        ]
    _publishers = [
        {'name': 'dept-health',
         'title': 'Department of Health',
         'contact-email': 'contact@doh.gov.uk',
         'category': 'department',
         'type': 'organization',
         'is_organization': True},
        {'name': 'national-health-service',
         'title': 'National Health Service',
         'contact-email': 'contact@nhs.gov.uk',
         'parent': 'dept-health',
         'category': 'grouping',
         'abbreviation': 'NHS',
         'type': 'organization',
         'is_organization': True},
        {'name': 'barnsley-primary-care-trust',
         'title': 'Barnsley Primary Care Trust',
         'contact-email': 'contact@barnsley.nhs.gov.uk',
         'parent': 'national-health-service',
         'category': 'alb',
         'type': 'organization',
         'is_organization': True},
        {'name': 'newham-primary-care-trust',
         'title': 'Newham Primary Care Trust',
         'contact-email': 'contact@newham.nhs.gov.uk',
         'parent': 'national-health-service',
         'category': 'alb',
         'type': 'organization',
         'is_organization': True},
        {'name': 'ons',
         'title': 'Office for National Statistics',
         'contact-email': 'contact@ons.gov.uk',
         'category': 'alb',
         'type': 'organization',
         'is_organization': True},
        {'name': 'cabinet-office',
         'title': 'Cabinet Office',
         'contact-email': 'contact@cabinet-office.gov.uk',
         'category': 'department',
         'type': 'organization',
         'is_organization': True},
        {'name': 'northern-ireland-spatial-data-infrastructure',
         'title': 'Northern Ireland Spatial Data Infrastructure',
         'category': 'alb',
         'type': 'organization',
         'is_organization': True},
        ]
    _roles = [('sysadmin', 'admin', 'system'),
              ]
    _user_publisher_memberships = [
        ('nhsadmin', 'admin', 'national-health-service'),
        ('nhseditor', 'editor', 'national-health-service'),
        ('user_d101', 'editor', 'national-health-service'),
        ('dh_admin', 'admin', 'dept-health'),
        ('co_admin', 'admin', 'cabinet-office'),
        ('co_editor', 'editor', 'cabinet-office'),
        ('barnsley_admin', 'admin', 'barnsley-primary-care-trust'),
        ('barnsley_editor', 'editor', 'barnsley-primary-care-trust'),
        ]
    _packages = [
        # Package edited on new form (June 2012)
        {'name': "directgov-cota",
         'title': "Directgov Article Ratings",
         'notes': "Ratings for all articles on the Directgov website.  One data file is available per day. Sets of files are organised by month on the download page",
         'license_id': 'uk-ogl',
         'tags': ["article", "cota", "directgov", "information", "ranking", "rating"],
         'groups': ['national-health-service'],
         'extras': {
             'access_constraints': '',
             'contact-email': '',
             'contact-name': '',
             'contact-phone': '',
             'foi-email': '',
             'foi-name': '',
             'foi-phone': '',
             'foi-web': '',
             'geographic_coverage': "000000: ",
             'geographic_granularity': '',
             'mandate': [''],
             'temporal_coverage-to': "2011-06-01",
             'temporal_coverage-from': "2010-01-01",
             'temporal_granularity': "",
             'theme-primary': "Society",
             'theme-secondary': "",
             'last_major_modification': "2000-01-01T00:00:00.000000",
             },
         'resources': [
             {'url': "http://innovate-apps.direct.gov.uk/cota/",
              'format': 'HTML',
              'description': "Directgov Article Ratings",
              #'cache_last_updated': datetime.datetime(year=2012,month=6,day=12,hour=17,minute=33),
              'cache_url': 'http://data.gov.uk/data/resource_cache/89471cf8-013f-4695-ad56-12c028e167b7/cota.html',
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
             'categories': "",
             'contact-email': '',
             'contact-name': '',
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
             'taxonomy_url': "http://www.metoffice.gov.uk/weather/uk/guide/key.html",
             'theme-primary': "Society",
             'update_frequency': "Real-time",
              'last_major_modification': "2000-01-01T00:00:00.000000",
             },
         'resources': [
             {"hash": "",
              "description": "70 Whitehall energy data",
              "format": "CSV",
              "mimetype_inner": None,
              # NB Commenting out those that have Null values for date/int types and other troublesome ones, as it is easiest
              #"webstore_last_updated": None,
              #"size": None,
              "mimetype": None,
              "cache_url": None,
              "name": None,
              "url": "http://data.carbonculture.net/orgs/cabinet-office/70-whitehall/reports/elec00.csv",
              #"cache_last_updated": None,
              "webstore_url": None,
              #"last_modified": None,
              #"resource_type": None,
              },
             ]
           },
        # Form - spend data
        {"name": "nhs-spend-over-25k-barnsleypct",
         "title": u"Spend over \u00a325k for Barnsley PCT",
         "notes": "A monthly updated list of all financial transactions over \u00a325k made by NHS Barnsley as part of the government's commitment to transparency in expenditure.",
         "license_id": "uk-ogl",
         "tags": ["barnsley", "department", "disclosure", "financial", "health", "invoices", "nhs", "pct", "spend", "transactions", "transparency"],
         "groups": ["barnsley-primary-care-trust"],
         "url": "http://www.barnsley.nhs.uk/2010-Pages/Your-NHS-Barnsley/Buying-and-Procurement/invoices-over-25k.htm",
         "extras": {
                "contact-name": "Finance Department",
                "contact-email": "enquiries@barnsleypct.nhs.uk",
                "geographic_coverage": "100000: England",
                "temporal_coverage-from": "2010-04-01",
                "temporal_granularity": "day",
                "date_updated": "2011-12-19",
                "temporal_coverage-to": "2012-02-29",
                "geographic_granularity": "",
                "taxonomy_url": "",
                "update_frequency": "monthly",
                "mandate": [""],
                "theme-primary": "Society",
                "date_update_future": "2012-01-24",
                'last_major_modification': "2000-01-01T00:00:00.000000",
             },
         "resources": [
                {"description": "April to September 2010",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/Publications/NHS%20Barnsley%20Invoices%20over%2025k%20to%20300910.csv",
                 },
                {"description": "October 2010",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/Publications/NHS%20Barnsley%20Invoices%20over%2025k%20Oct%202010.csv",
                 },
                {"description": "November 2010",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/Publications/NHS%20Barnsley%20Invoices%20spend%20over%2025K%20Nov%202010.csv",
                 },
                {"description": "December 2010",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Dec%202010.csv",
                 },
                {"description": "January 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Jan%202011.csv",
                 },
                {"description": "February 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Feb%202011.csv",
                 },
                {"description": "March 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Mar%202011.csv",
                 },
                {"description": "April 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Apr%202011.csv",
                 },
                {"description": "May 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20May%202011.csv",
                 },
                {"description": "June 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Jun%202011.csv",
                 },
                {"description": "July 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Jul%202011.csv",
                 },
                {"description": "August 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Aug%202011.csv",
                 },
                {"description": "September 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Sep%202011.csv",
                 },
                {"description": "October 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Oct%202011.csv",
                 },
                {"description": "November 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Nov%202011.csv",
                 },
                {"description": "December 2011",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Dec%202011.csv",
                 },
                {"description": "January 2012",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Jan%202012.csv",
                 },
                {"description": "February 2012",
                 "format": "CSV",
                 "url": "http://www.barnsley.nhs.uk/Downloads/NHS%20Barnsley%20Invoices%20over%2025k%20Feb%202012.csv",
                 },
                {"description": "Web page about the data",
                 "format": 'HTML',
                 "url": "http://www.barnsley.nhs.uk/2010-Pages/Your-NHS-Barnsley/Buying-and-Procurement/invoices-over-25k.htm",
                 'resource_type': 'documentation',
                 },
                ],
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
             'temporal_coverage-to': "",
             'temporal_granularity': "",
             'theme-primary': "Society",
             'update_frequency': "quarterly",
             'last_major_modification': "2000-01-01T00:00:00.000000",
             },
         'resources': [
             {"hash": "",
              "description": "2011 Q4 - January GDP update",
              "format": "XML",
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
              #"resource_type": None,
              "extras": {
                  "hub-id": "77-250599",
                  },
              },
             {"hash": "",
              "description": "2011 Q4 - February Labour Market update",
              "format": "XML",
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
              #"resource_type": None,
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
         'tags': ['infoMapAccessService'],
         'groups': ['northern-ireland-spatial-data-infrastructure'],
         'extras': {
             'bbox-east-long': "-5.40566902640608",
             'temporal_coverage-from': "",
             'resource-type': "service",
             'bbox-north-lat': "55.3184340550243",
             'coupled-resource': '[{"href": ["http://webservices.spatialni.gov.uk/arcgis/services/LPS/CadastreNI/MapServer/WMSServer"], "uuid": ["http://webservices.spatialni.gov.uk/arcgis/services/LPS/CadastreNI/MapServer/WMSServer"], "title": []}]',
             'guid': "5b850805-8c62-4521-9dec-a448dfabe7f3",
             'bbox-south-lat': "54.0295252443606",
             'temporal_coverage-to': "",
             'spatial-reference-system': "CRS:84",
             'spatial': '{"type":"Polygon","coordinates":[[[-5.40566902640608, 54.0295252443606],[-5.40566902640608, 55.3184340550243], [-8.17548890898914, 55.3184340550243], [-8.17548890898914, 54.0295252443606], [-5.40566902640608, 54.0295252443606]]]}',
             'access_constraints': '["no limitations"]',
             'contact-name': '',
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
             'metadata-language': "eng",
             # Deliberately missing for test
             #'last_major_modification': "2000-01-01",
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
              #'resource_type': None,
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
    _task_statuses = [
        {'package_name': 'directgov-cota',
         'resource_index': 0,
         'task_type': 'archiver',
         'key': 'celery_task_id',
         'value': '0a4b97d9-426e-412f-ad31-90479d88e684',
         'state': '',
         'error': '',
         'last_updated': datetime.datetime(2012, 07, 23, 22, 13, 8, 125505),
         },
        {'package_name': 'directgov-cota',
         'resource_index': 0,
         'task_type': 'qa',
         'key': 'openness_score',
         'value': '0',
         'state': '',
         'error': '',
         'last_updated': datetime.datetime(2012, 07, 23, 01, 10, 49, 842923),
         },
        {'package_name': 'directgov-cota',
         'resource_index': 0,
         'task_type': 'qa',
         'key': 'openness_score_reason',
         'value': 'Could not download it',
         'state': '',
         'error': '',
         'last_updated': datetime.datetime(2012, 07, 23, 01, 10, 49, 843123),
         },
        {'package_name': 'directgov-cota',
         'resource_index': 0,
         'task_type': 'qa',
         'key': 'openness_score_failure_count',
         'value': '5',
         'state': '',
         'error': '',
         'last_updated': datetime.datetime(2012, 07, 23, 01, 10, 49, 843123),
         },
        {'package_name': 'nhs-spend-over-25k-barnsleypct',
         'resource_index': 0,
         'task_type': 'qa',
         'key': 'celery_task_id',
         'value': '5231be73-f5bf-4baf-b18b-3ac8c364db5b',
         'state': '',
         'error': 'CkanError: ckan failed to update resource, status_code (404)',
         'last_updated': datetime.datetime(2012, 07, 23, 01, 10, 49, 842923),
         }
        ]

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
        cls.create_users(cls._users)
        cls.create_groups(cls._publishers)
        cls.create_roles(cls._roles)
        cls.create_user_publisher_memberships(cls._user_publisher_memberships)
        cls.create_arbitrary(cls._packages)
        cls.create_task_statuses(cls._task_statuses)

    @classmethod
    def create_dgu_test_users(cls):
        # and their rights (assumes publishers are created already)
        ckan.lib.activity.logger.disabled = 1
        cls.create_users(cls._users)
        model.repo.commit_and_remove() # due to bug in create_users
        cls.create_roles(cls._roles)
        cls.create_user_publisher_memberships(cls._user_publisher_memberships)

    @classmethod
    def create_task_statuses(cls, task_statuses):
        for task_status in task_statuses:
            # identify the entity
            if 'package_name' in task_status:
                pkg = model.Package.get(task_status['package_name'])
                assert pkg
                if 'resource_index' in task_status:
                    entity = pkg.resources[task_status['resource_index']]
                else:
                    entity = pkg
            else:
                assert 0, 'Unknown entity_id'
            entity_type = entity.__class__.__name__.lower()

            model.repo.new_revision()

            # see if the TaskStatus object exists already
            q = model.Session.query(model.TaskStatus) \
                .filter_by(entity_id=entity.id) \
                .filter_by(entity_type=entity_type) \
                .filter_by(task_type=task_status['task_type']) \
                .filter_by(key=task_status['key'])
            if q.count():
                # edit existing object
                ts = q.first()
                for field_name in ['value', 'state', 'error', 'last_updated']:
                    value = task_status.get(field_name)
                    setattr(ts, field_name, value)
            else:
                # create new object
                ts = model.TaskStatus(entity_id=entity.id,
                                      entity_type=entity_type,
                                      task_type=task_status['task_type'],
                                      key=task_status['key'],
                                      value=task_status['value'],
                                      state=task_status.get('state', ''),
                                      error=task_status.get('error', ''),
                                      last_updated=task_status.get('last_updated'))
                model.Session.add(ts)
        model.repo.commit_and_remove()

    @classmethod
    def ons_package(cls):
        return model.Package.by_name(u'gdp_and_the_labour_market_')

    @classmethod
    def old_form_package(cls):
        return model.Package.by_name(u'cabinet-office-energy-use')

    @classmethod
    def form_package(cls):
        return model.Package.by_name(u'directgov-cota')
