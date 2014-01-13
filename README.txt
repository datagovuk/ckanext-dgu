===================================
ckanext-dgu - data.gov.uk extension
===================================

This is an extension to CKAN that provides customisations specifically for the data.gov.uk project.

The official version is available at: https://github.com/datagovuk/ckanext-dgu

Contributions from 1st March 2012 are by the Cabinet Office. It is Crown Copyright and opened up under both the Open Government Licence (OGL) (which is compatible with Creative Commons Attibution License) and the GNU Affero General Public License (AGPL) v3.0. Before 1st March 2012, contributions are Copyright (c) 2010-2012 Open Knowledge Foundation. This material is open and licensed under the GNU Affero General Public License (AGPL) v3.0.

OGL terms: http://www.nationalarchives.gov.uk/doc/open-government-licence/
AGPL terms: http://www.fsf.org/licensing/licenses/agpl-3.0.html

Related extensions that data.gov.uk use in addition are: ckanext-archiver, ckanext-harvest, ckanext-spatial, ckanext-os, ckanext-qa, ckanext-social

Plugins
=======

This extension contains a number of elements, principally:

 * dgu_form - DGU's package form (??) - includes a number of custom fields such as temporal_coverage and geographic_coverage.
 * Harvest Object inserted into the CKAN package view page.
 * gov_daily - a script (for running daily) that save the database dumps for end-users (JSON/CSV) and backups (SQL).
 * ons_loader - an import script for data from the Office of National Statistics.
 * cospread - an import script for packages listed in a standardised spreadsheet format.
 * various other command-line utilities

dgu_form
--------

ckanext.dgu.plugin:DguForm
ckanext.dgu.controllers.package:PackageController
Based on PackageController but at /dataset/* rather than /package/* and adds the delete function. Proxy for getting Drupal comments (only for running in paster). NO FORM HERE

dgu_drupal_auth
---------------

ckanext.dgu.plugin:DrupalAuthPlugin
ckanext.dgu.authentication.drupal_auth:DrupalAuthMiddleware

Middleware to log-in the user based on Drupal cookies and requests to Drupal.

dgu_auth_api
------------

ckanext.dgu.plugin:AuthApiPlugin
ckanext.dgu.authorize
Changes permissions:
* hierarchy structure - edit package/group if is an editor for the group or an admin for the group or its parents.
* All package creations/edits need an API key - no anonymous ones
* UKLP packages can't be edited through the form or API - only by harvesting (unless sysadmin)
* ONS packages can't be edited through the form or API - only by ONS loader (unless sysadmin)
* Packages can only be deleted by sysadmin or UKLP packages by their editor/admin.
* Users can only be viewed by the user and sysadmin
* User list can only be viewed by sysadmin, editors, admins.

dgu_publishers
--------------

ckanext.dgu.plugin:PublisherPlugin
ckanext.dgu.controllers.publisher:PublisherController

Sets 'ckan.auth.profile' to 'publisher' (and same for harvesting: 'ckan.harvest.auth.profile' = 'publisher').
Publisher controller, based on Group:
* Publisher browse page includes hierarchy, alpha-browse and search.
* Apply to be a publisher editor or admin.
* Edit admins/editors for a publisher
* Publisher read shows publisher hierarchy, search pane with results and pager
* Display publisher's admins/editors for appropriate users.
* Report pages - users not assigned to groups, groups without admins, publishers vs users, users
When user is created, flashes "You can now <a>apply for publisher access</a>"

dgu_theme
--------

ckanext.dgu.plugin:ThemePlugin
ckanext.dgu.controllers.data:DataController
ckanext.dgu.controllers.tag:TagController
ckanext.dgu.controllers.reports:ReportsController
from ckanext.dgu.lib import helpers
ckanext/dgu/theme/templates
ckanext/dgu/theme/public

Data, Tag and Reports Controllers. Templates, helper functions. 
Random extras:
* Viewing user names (e.g. in History) change them for dept if not editor/admin.
* Add 'Vary: Cookie' header to all responses.

dgu_search
----------

ckanext.dgu.plugin:SearchPlugin
from ckanext.dgu.search_indexing import SearchIndexing

Add fields to search index. Default sort-by. Escape SOLR characters. Search field weighting adjusted.

dgu_publisher_form
------------------

ckanext.dgu.forms.publisher_form:PublisherForm

New group form, type 'publisher' with schema. Added fields: contact, foi contacts, category, abbreviation.

dgu_dataset_form
----------------

ckanext.dgu.forms.dataset_form:DatasetForm
ckanext.dgu.forms.validators
ckanext.dgu.schema:GeoCoverageType

New dataset form. Lots of schema and validation customisation.

dgu_api
-------

ckanext.dgu.plugin:ApiPlugin
ckanext.dgu.controllers.api:DguApiController
ckanext.dgu.controllers.api:DguReportsController
ckanext.dgu.lib.reports

Util API for Drupal - latest-datasets (front page), dataset-count (front page), revisions (unused). 
Reports, starting with organisation_resources.

dgu_resource_updates/dgu_resource_url_updates
---------------------------------------------

ckanext.dgu.plugin:ResourceModificationPlugin
ckanext.dgu.plugin:ResourceURLModificationPlugin

When a resource is created/deleted/URL-changed, this updates the last_major_modification date of its package.

Non-plugin code
===============

ckanext/dgu/schema.py - mostly not used now
ckanext/dgu/drupalclient.py - for getting user info from Drupal
dgu/ckanext/dgu/bin/ - scripts used at one time or another
dgu/ckanext/dgu/commands/ - scripts used at one time or another
dgu/ckanext/dgu/cospread/ - v old scripts for importing spreadsheets of metadata
dgu/ckanext/dgu/ons/ - scripts for importing ONS data

Install
=======

This is how to install ckanext-dgu, ckan and their dependencies into a python virtual environment::

    virtualenv pyenv
    pip -E pyenv install -e git+https://github.com:okfn/ckanext-dgu.git#egg=ckanext-dgu
    pip -E pyenv install -e git+https://github.com/okfn/ckan.git#egg=ckan
    pip -E pyenv install -r pyenv/src/ckan/pip-requirements.txt
    pip -E pyenv install -r pyenv/src/ckanext-dgu/pip-requirements.txt

There are plenty of other little details about getting CKAN running under Apache, SOLR config etc in the CKAN README.

When configuring Apache, DGU enables some modules SSL and for ckanext-os. This is the complete list::
    sudo a2enmod proxy wsgi headers proxy_http rewrite ssl


Configuration
=============

Different parts of the DGU extension require options to be set in the
CKAN configuration file (.ini) in the [app:main] section

To use the DGU package form specify::

    ckan.plugins = dgu_form dgu_package_form

For the Drupal RPC connection (for user data etc.) supply the hostname, 
and credentials for HTTP Basic Authentication (if necessary)::

    dgu.xmlrpc_domain = drupal.libre.gov.fr:80
    dgu.xmlrpc_username = ckan
    dgu.xmlrpc_password = letmein

The DGU-version of the SOLR schema is required instead of the CKAN SOLR schema. Whether you use a single or mult-core SOLR setup, you'll need a link to the DGU SOLR schema like this::

    sudo ln -s /home/okfn/pyenv/src/ckanext-dgu/config/solr/schema-1.4-dgu.xml /etc/solr/conf/schema.xml


Initialise database
===================

Creating the database is as usual for CKAN::

    db=dgu
    db_user=dgu
    sudo -u postgres createuser -S -D -R -P $db_user
    sudo -u postgres createdb -O $db_user $db

And because we usually use ckanext-dgu also with ckanext-spatial, then PostGIS needs setting up too::

    sudo -u postgres psql -d $db -f /usr/share/postgresql/9.1/contrib/postgis-1.5/postgis.sql -v ON_ERROR_ROLLBACK=on
    sudo -u postgres psql -d $db -f /usr/share/postgresql/9.1/contrib/postgis-1.5/spatial_ref_sys.sql
    sudo -u postgres psql -d $db -c "ALTER TABLE spatial_ref_sys OWNER TO $db_user;"
    sudo -u postgres psql -d $db -c "ALTER TABLE geometry_columns OWNER TO $db_user;"

(For more info on that, see the README for ckanext-spatial.)

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


Assets
======

The DGU theme uses assets (images, javascript, css) from this repo and the shared assets repo::

    https://github.com/datagovuk/shared_dguk_assets

Both repos should be cloned next to each other on developer and server machines. If this is not possible then you need to set the dgu.shared_assets_timestamp_path config option to tell CKAN where the shared assets timestamp file is. e.g.::

    dgu.shared_assets_timestamp_path = /vagrant/src/shared_dguk_assets/assets/timestamp

Assets are stored in the repo in 'source' form - the form easiest for developers to edit them in. Before they can be served, Grunt must be run on both repos to create the 'public' versions of these files. This does concatenation, minification, compilation of the less, and recording a timestamp (see Gruntfile.js for details).

Source:

    images:     ckanext/dgu/theme/src/images
    javascript: ckanext/dgu/theme/src/scripts
    css (less): ckanext/dgu/theme/src/css

And when you run grunt, you get:

    images:     ckanext/dgu/theme/public/images
    javascript: ckanext/dgu/theme/public/scripts
    css:        ckanext/dgu/theme/public/css
    timestamp:  ckanext/dgu/theme/timestamp.py

Read more about Grunt installation and running it: https://github.com/datagovuk/shared_dguk_assets/blob/master/README.md

The shared assets need to be served at /assets. On a deployment server, setup nginx or apache to do this. A developer running under paster will find that the shared assets are served autoimatically, as long as the repo is cloned alongside ckanext-dgu and that this config option is not set: dgu.shared_assets_timestamp_path.


Tests
=====

Unit and functional tests
-------------------------

To test the DGU extension you need the setup with CKAN (see above) and creation of a configured pyenv/src/ckan/development.ini (see http://docs.ckan.org/en/latest/install-from-source.html ).

To run the tests::

    {pyenv}/bin/activate
    cd {pyenv}/ckanext-dgu
    nosetests --ckan ckanext/dgu/tests/

or run them from another directory by specifying the test.ini::

    nosetests --ckan --with-pylons={pyenv}/src/ckanext-dgu/test.ini {pyenv}/src/ckanext-dgu/ckanext/dgu/tests/

You can either run the 'quick and dirty' tests with SQLite or more comprehensively with PostgreSQL. Set ``--with-pylons`` to point to the relevant configuration - either ``test.ini`` or ``test-core.ini`` (both from the ckanext-dgu repo, not the ckan one). For more information, see http://docs.ckan.org/en/latest/install-from-source.html . 

Browser tests
-------------

Selenium is used to test a site is operating to a basic minimum standard, and specific checks on javascript elements.

To run the Selenium tests, TODO


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
