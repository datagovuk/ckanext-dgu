===========================
dgu - data.gov.uk extension
===========================


Setup for loaders only
======================

It is simpler to set-up to run the loaders, because they don't require
CKAN to be installed::

    virtualenv pyenv
    pip -E pyenv install -e hg+https://knowledgeforge.net/ckan/ckanclient#egg=ckanclient
    pip -E pyenv install -e hg+https://knowledgeforge.net/ckan/ckanext#egg=ckanext
    pip -E pyenv install -e hg+https://knowledgeforge.net/ckan/dgu#egg=dgu

Now you can activate the environment and run the scripts::
    . pyenv/bin/activate
    ons_loader --help


Setup with CKAN
===============

The DGU forms and form API work with a CKAN install. In this case, you can 
install dgu into the ckan virtual environment directly::

    pip -E ckan/pyenv install -e hg+https://knowledgeforge.net/ckan/dgu#egg=dgu

Now in CKAN you can specify the dgu forms in the config. e.g. in demo.ckan.net.ini specify::

    package_form = package_gov3


Tests
=====

To test the DGU extension you need the setup with CKAN (see above).

To run the tests::

    ckan/pyenv/bin/activate
    cd ckan/pyenv/src/dgu
    nosetests ckanext/dgu/tests/
