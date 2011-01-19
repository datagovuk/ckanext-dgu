from setuptools import setup, find_packages

setup(
    name='ckanext-dgu',
    version='0.3',
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license='AGPL',
    url='http://knowledgeforge.net/ckan/',
    description='CKAN DGU extensions',
    keywords='data packaging component tool server',
    install_requires=[
        'swiss',
        'ckanclient>=0.5',
        'xlrd>=0.7.1',
        'xlwt>=0.7.2',
        #'ckanext', when it is released
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points="""
        [console_scripts]
        ons_loader = ckanext.dgu.ons:load
        cospread_loader = ckanext.dgu.cospread:load
        change_licenses = ckanext.dgu.scripts.change_licenses_cmd:command
        transfer_url = ckanext.dgu.scripts.transfer_url_cmd:command
        ons_analysis = ckanext.dgu.scripts.ons_analysis_cmd:command
        ofsted_fix = ckanext.dgu.scripts.ofsted_fix_cmd:command

        [ckan.forms]
        gov3 = ckanext.dgu.forms.package_gov3:get_gov3_fieldset

        [curate.actions]
        report=ckanext.dgu.curation:report
    """,
    test_suite = 'nose.collector',
)
