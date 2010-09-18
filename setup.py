from setuptools import setup, find_packages

setup(
    name='dgu',
    version='0.1',
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license='AGPL',
    url='http://knowledgeforge.net/ckan/',
    description='CKAN DGU extensions',
    keywords='data packaging component tool server',
    install_requires=[
        'ckanclient',
        'xlrd>=0.7.1',
        'xlwt>=0.7.2',
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points="""
        [console_scripts]
        ons_loader = ckanext.dgu.ons:load
    """,
    test_suite = 'nose.collector',
)
