===================================
ckanext-dgu - data.gov.uk extension
===================================


Setup for loaders only
======================

It is simpler to set-up to run the loaders, because they don't require
CKAN to be installed::

    virtualenv pyenv
    pip -E pyenv install -e hg+http://bitbucket.org/okfn/ckanclient#egg=ckanclient
    pip -E pyenv install -e hg+http://bitbucket.org/okfn/ckanext#egg=ckanext
    pip -E pyenv install -e hg+http://bitbucket.org/okfn/ckanext-dgu#egg=ckanext-dgu

Now you can activate the environment and run the scripts::
    . pyenv/bin/activate
    ons_loader --help


Setup with CKAN
===============

The DGU forms and form API work with a CKAN install. In this case, you can 
install dgu into the ckan virtual environment directly::

    pip -E ckan/pyenv install -e hg+http://bitbucket.org/okfn/ckanext-dgu#egg=ckanext-dgu

Now in CKAN you can specify the dgu forms in the config. e.g. in demo.ckan.net.ini specify::

    package_form = package_gov3


Configuation
============

Different parts of the DGU extension require options to be set in the
CKAN configuration file (.ini) in the [app:main] section

For the form API::

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
