def get_ons_producers():
    # Pasted in from http://www.statistics.gov.uk/hub/statistics-producers/index.html
    # and titles commented out.
    ons_depts = '''
#Government Statistical Departments
Business, Innovation and Skills
Child Maintenance and Enforcement Commission
Communities and Local Government
Culture, Media and Sport
Defence
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
National Treatment Agency
Northern Ireland Statistics and Research Agency
Office of Qualifications and Examinations Regulation
Office for National Statistics
Passenger Focus
Scottish Government
Transport
Welsh Assembly Government
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
                  ]
    return org_names
