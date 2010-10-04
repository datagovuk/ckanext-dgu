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

(note, for the time being, the ckanclient must be installed before dgu to 
ensure you get the latest source, not the old release.)

Now you can activate the environment and run the scripts::
    . pyenv/bin/activate
    ons_loader --help


Setup with CKAN
===============

The DGU forms work with a CKAN install. In this case, you can install dgu
into the ckan virtual environment directly::

(for the time being you must delete from the ckan environment the existing 
ckanclient and put in the latest)

    pip -E ckan/pyenv install -e hg+https://knowledgeforge.net/ckan/dgu#egg=dgu

Now in CKAN you can specify the dgu forms in the config.


Tests
=====

To test the DGU extension you need the setup with CKAN (see above).

To run the tests::

    {pyenv}/bin/activate
    cd dgu
    nosetests ckanext/dgu/tests/
