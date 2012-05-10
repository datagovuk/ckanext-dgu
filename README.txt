===================================
ckanext-dgu - data.gov.uk extension
===================================

This is an extension to CKAN that provides customisations specifically for the data.gov.uk project:

 * DGU's package form - includes a number of custom fields such as temporal_coverage and geographic_coverage.
 * Harvest Object inserted into the CKAN package view page.
 * gov_daily - a script (for running daily) that save the database dumps for end-users (JSON/CSV) and backups (SQL).
 * ons_loader - an import script for data from the Office of National Statistics.
 * cospread - an import script for packages listed in a standardised spreadsheet format.
 * various other command-line utilities


Install
=======

This is how to install ckanext-dgu, ckan and their dependencies into a python virtual environment::

    virtualenv pyenv
    pip -E pyenv install -e git+https://github.com:okfn/ckanext-dgu.git#egg=ckanext-dgu
    pip -E pyenv install -e git+https://github.com/okfn/ckan.git#egg=ckan
    pip -E pyenv install -r pyenv/src/ckan/pip-requirements.txt
    pip -E pyenv install -r pyenv/src/ckanext-dgu/pip-requirements.txt


Configuration
=============

Different parts of the DGU extension require options to be set in the
CKAN configuration file (.ini) in the [app:main] section

To use the DGU form specify::

    package_form = package_gov3

To enable the Form API::

    ckan.plugins = dgu_form_api

For the Drupal RPC connection (for user data etc.) supply the hostname, 
and credentials for HTTP Basic Authentication (if necessary)::

    dgu.xmlrpc_domain = drupal.libre.gov.fr:80
    dgu.xmlrpc_username = ckan
    dgu.xmlrpc_password = letmein

The DGU-version of the SOLR schema is required instead of the CKAN 1.3 SOLR schema. Whether you use a single or mult-core SOLR setup, you'll need a link to the DGU SOLR schema like this::

    sudo ln -s /home/okfn/pyenv/src/ckanext-dgu/config/solr/schema-1.3-dgu.xml /etc/solr/conf/schema.xml


Usage
=====

There is a front-page added to CKAN which describes the Catalogue APIs. The usual CKAN front-page has been moved to /ckan/ .

e.g.::

    http://127.0.0.1:5000/ckan/


Scripts
=======

There are a number of command-line scripts for processing data. To run one of these, you should activate the environment first. For example to load in some ONS data you might start like this::

    . pyenv/bin/activate
    ons_loader --help


Tests
=====

To test the DGU extension you need the setup with CKAN (see above) and creation of a configured pyenv/src/ckan/development.ini (see http://docs.ckan.org/en/latest/install-from-source.html ).

To run the tests::

    {pyenv}/bin/activate
    cd {pyenv}/ckanext-dgu
    nosetests --ckan ckanext/dgu/tests/

or run them from another directory by specifying the test.ini::

    nosetests --ckan --with-pylons={pyenv}/src/ckanext-dgu/test.ini {pyenv}/src/ckanext-dgu/ckanext/dgu/tests/

You can either run the 'quick and dirty' tests with SQLite or more comprehensively with PostgreSQL. Set ``--with-pylons`` to point to the relevant configuration - either ``test.ini`` or ``test-core.ini`` (both from the ckanext-dgu repo, not the ckan one). For more information, see http://docs.ckan.org/en/latest/install-from-source.html . 

Test issues
-----------

Address and Connection errors
+++++++++++++++++++++++++++++

* ``socket.error: [Errno 98] Address already in use``
* ``error: [Errno 111] Connection refused``

These errors usually means a previous run of the tests has not cleaned up the Mock Drupal process. You can verify that::

    $ ps a | grep mock_drupal
    4748 pts/8    S      0:00 /home/dread/hgroot/pyenv-dgu/bin/python /home/dread/hgroot/pyenv-dgu/bin/paster --plugin=ckanext-dgu mock_drupal run -q

Now kill it before running the tests again::

    $ kill 4748

Config errors
+++++++++++++

* ``DrupalXmlRpcSetupError: Drupal XMLRPC not configured.``

The missing settings that result in this error are to be found in {pyenv}/src/ckanext-dgu/test-core.ini which is also imported into {pyenv}/src/ckanext-dgu/test.ini, so make sure you are specifying either of these config files in your nosetests ``--with-pylons`` parameter.

* ``ckan.lib.search.common.SearchIndexError: HTTP code=400, reason=ERROR: [f752f33380e3eec1379cfb89e0fdded8] multiple values encountered for non multiValued field parent_publishers: [london-borough-of-barnet, local-authorities]``

This is due to SOLR using the CKAN SOLR schema, rather than the specific DGU one. Change it using the ``ln -s`` command above, followed by stopping and starting SOLR.


Documentation
=============

DGU is an extension for CKAN: http://ckan.org

This README file is part of the DGU Developer Documentation, stored in the
ckanext-dgu repo at ``ckanext-dgu/doc``. 

The Developer Docs can be built using `Sphinx <http://sphinx.pocoo.org/>`_::

      python setup.py build_sphinx
