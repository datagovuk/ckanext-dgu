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

    ckan/pyenv/bin/activate
    cd ckan/pyenv/src/dgu
    nosetests ckanext/dgu/tests/


Documentation
=============

DGU is an extension for CKAN: http://ckan.org

This README file is part of the DGU Developer Documentation, viewable at:
http://knowledgeforge.net/ckan/doc/ckanext-dgu/index.html and stored in the
ckanext-dgu repo at ``ckanext-dgu/doc``. 

The Developer Docs are built using `Sphinx <http://sphinx.pocoo.org/>`_::

      python setup.py build_sphinx

The docs are uploaded via dav.