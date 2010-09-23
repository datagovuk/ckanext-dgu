===========================
dgu - data.gov.uk extension
===========================

Quickstart
==========

Getting the code installed::

    hg clone https://knowledgeforge.net/ckan/dgu
    hg clone https://knowledgeforge.net/ckan/ckanext
    virtualenv pyenv-dgu
    . pyenv-dgu/bin/activate
    cd dgu
    python setup.py develop
    pip -E ../pyenv-dgu install -e ../ckanext

Now you can run the scripts::
    ( If you've not already, you need to: . ../pyenv-dgu/bin/activate )
    ons_loader


Tests
=====

To test this extension you need some modules installed into you dgu
virtual python environment. Here we install the source (this may not be
necessary in future, but we need the latest code which isn't released as of
writing.)
    
    hg clone https://knowledgeforge.net/ckan/ckanclient
    hg clone https://knowledgeforge.net/ckan/hg ckan
    pip -E ../pyenv-dgu install -e ckanclient
    pip -E ../pyenv-dgu install -e ckan

To run the tests::

    {pyenv-dgu}/bin/activate
    cd dgu
    nosetests ckanext/dgu/tests/
    