def get_ons_producers():
    # Pasted in from http://www.statistics.gov.uk/hub/statistics-producers/index.html
    # and titles commented out.
    # When you add something to this:
    # 1. Run: generate_test_organisations -D data.gov.uk:80 -U username -P password
    # 2. Any organisations that can't be found, check on data.gov.uk.
    #     * Either the mapping needs to be improved:
    #         ckanext/dgu/schema.py:organisation_name_mapping
    #     * or the organisation needs adding:
    #         https://www.data.gov.uk/node/add/publisher
    #     Then go back to step 1 until errors are elimenated.
    # 3. Test with: ckanext.dgu.tests.ons.test_ons_importer.TestOnsImporter.test_dept_to_organisation
    # 4. Commit changes to lots_of_orgs.json etc.
    ons_depts = '''
#Government Statistical Departments
Business, Innovation and Skills
Child Maintenance and Enforcement Commission
Communities and Local Government
Culture, Media and Sport
Defence
Justice (Northern Ireland)
Education
Energy and Climate Change
Enterprise, Trade and Investment (Northern Ireland)
Environment, Food and Rural Affairs
Food Standards Agency
Forestry Commission
General Register Office for Scotland
HM Revenue and Customs
HM Treasury
Health
Health and Safety Executive
Health Protection Agency
Home Office
ISD Scotland (part of NHS National Services Scotland)
Information Centre for Health and Social Care
International Development
Justice
Marine Management Organisation
National Treatment Agency
NHS Information Centre for Health and Social Care
National Records of Scotland
National Treatment Agency
Northern Ireland Statistics and Research Agency
Office for National Statistics
Office for Standards in Education, Children\'s Services and Skills
Office of Qualifications and Examinations Regulation
Passenger Focus
Scottish Government
Transport
Welsh Government
Work and Pensions
#Other statistics producers
Civil Aviation Authority
Higher Education Statistics Agency
#International statistics organisations
Eurostat
'''
    org_names = [org_name for org_name in ons_depts.split('\n') if org_name and not org_name.startswith('#')]
    # These are other sources seen in real ONS data (that have caused import warnings)
    org_names += ['National Health Service in Scotland',
                  'Police Service of Northern Ireland (PSNI)',
                  'NHS National Services Scotland',
                  'Office of the First and Deputy First Minister',
                  'Culture, Arts and Leisure (Northern Ireland)',
                  'Environment (Northern Ireland)',
                  'Finance and Personnel (Northern Ireland)',
                  'Health, Social Services and Public Safety (Northern Ireland)',
                  'Regional Development (Northern Ireland)',
                  'Social Development (Northern Ireland)',
                  'Employment and Learning (Northern Ireland)',
                  'Welsh Government',
                  ]
    return org_names
