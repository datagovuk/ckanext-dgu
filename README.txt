===================================
ckanext-dgu - data.gov.uk extension
===================================


Dependencies
============


Setup
=====

You need ckan installed as well as various other dependencies listed in
pip-requirements.txt::

    virtualenv pyenv
    pip -E pyenv install -e .
    pip -E pyenv install -e hg+http://bitbucket.org/okfn/ckan#egg=ckan
    pip -E pyenv install -r pip-requirements.txt

Now you can activate the environment and run the scripts::

    . pyenv/bin/activate
    ons_loader --help


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


Tests
=====

To test the DGU extension you need the setup with CKAN (see above).

To run the tests::

    {pyenv}/bin/activate
    cd {pyenv}/ckanext-dgu
    nosetests --ckan ckanext/dgu/tests/

or run them from another directory by specifying the test.ini::

    nosetests {pyenv}/src/ckanext-dgu/ckanext/dgu/tests/ --ckan --with-pylons={pyenv}/src/ckanext-dgu/test.ini {pyenv}/src/ckanext-dgu/ckanext/dgu/tests/

You can either run the 'quick and dirty' tests with SQLite or more comprehensively with PostgreSQL. Set ``--with-pylons`` to point to the relevant configuration - either ``test.ini`` or ``test-core.ini`` (both from the ckanext-dgu repo, not the ckan one). For more information, see the CKAN README.txt. 

Test issues
-----------

Connection errors
+++++++++++++++++

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

Mock Drupal process
+++++++++++++++++++

If you get "Address in use" then it means a previous run of the tests has not cleaned up the Mock Drupal process. You can verify that::

    ps |grep paster


Documentation
=============

DGU is an extension for CKAN: http://ckan.org

This README file is part of the DGU Developer Documentation, viewable at:
http://knowledgeforge.net/ckan/doc/ckanext-dgu/index.html and stored in the
ckanext-dgu repo at ``ckanext-dgu/doc``. 

The Developer Docs are built using `Sphinx <http://sphinx.pocoo.org/>`_::

      python setup.py build_sphinx

The docs are uploaded via dav.