#!/bin/sh

####################################################
## Have previously *manually* run the following 
## commands
##
## sudo -u postgres createdb ckantest
## sudo -u postgres createuser ckanuser
####################################################

####################################################
## Get and setup the code that we require
####################################################
echo `pwd`

## Pre-setup some stuff.
## make sure that we get an up-to-date version of python-dateutil before a recent version
## is imported.
pip install python-dateutil==1.5
python -c 'import pkg_resources' || curl http://python-distribute.org/distribute_setup.py | python

[ -d ckanext-dgu ] || git clone git@github.com:datagovuk/ckanext-dgu.git
cd ckanext-dgu
git pull origin master
python setup.py develop
cd ..

[ -d ckan ] || git clone git@github.com:datagovuk/ckan.git
cd ckan
git checkout release-v1.7.1-dgu
git pull origin release-v1.7.1-dgu
python setup.py develop
sed -i '/ckan@release-v1.7.1#egg=ckan/d' pip-requirements.txt 
pip install -r pip-requirements.txt
pip install -r pip-requirements-test.txt
git checkout pip-requirements.txt
cd ..

[ -d ckanext-spatial ] || git clone git@github.com:datagovuk/ckanext-spatial.git
cd ckanext-spatial
pip install -r pip-requirements.txt
python setup.py develop
cd ..

git@github.com:okfn/datautildate.git
[ -d datautildate ] || git clone git@github.com:okfn/datautildate.git
cd datautildate
git pull origin master
python setup.py develop
cd ..


[ -d ckanext-harvest ] || git clone git@github.com:datagovuk/ckanext-harvest.git
cd ckanext-harvest
git pull origin master
python setup.py develop
pip install -r pip-requirements.txt
cd ..

[ -d ckanext-qa ] || git clone git@github.com:datagovuk/ckanext-qa.git
cd ckanext-qa
git fetch
git checkout temp_working
git pull origin temp_working
python setup.py develop
cd ..

[ -d ckanext-importlib ] || git clone git@github.com:okfn/ckanext-importlib.git
cd ckanext-importlib
git pull origin master
python setup.py develop
cd ..

####################################################
## Change configuration
####################################################
echo `pwd`
cd ckan 
[ -e development.ini ] || paster make-config ckan development.ini

# Uncomment solr
# sed -i '.bak'  's/\#solr_url/solr_url/g' development.ini
cd ..

####################################################
## Run the tests !!
####################################################

cd ckanext-dgu
echo `pwd`
echo "Running tests"
nosetests --with-pylons=test-core.ini ckanext/dgu/tests/
