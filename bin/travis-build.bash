#!/bin/bash
set -e # stop on error
set -x # echo on

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install postgresql-$PGVERSION solr-jetty libcommons-fileupload-java:amd64=1.2.2-1

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/datagovuk/ckan
cd ckan
#export latest_ckan_release_branch=`git branch --all | grep remotes/origin/release-v | sort -r | sed 's/remotes\/origin\///g' | head -n 1`
export ckan_branch=release-v2.2-dgu
echo "CKAN branch: $ckan_branch"
git checkout $ckan_branch
python setup.py develop
pip install --upgrade setuptools
pip install -r requirements.txt --allow-all-external
pip install -r dev-requirements.txt --allow-all-external
cd -

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini
cd -

echo "SOLR config..."
# solr is multicore for tests on ckan master now, but it's easier to run tests
# on Travis single-core still.
# see https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini

echo "Installing ckanext-dgu and its requirements..."
python setup.py develop
# Seems like ckanext-taxonomy dependency 'python-skos' won't even start
# installing without rdflib already being installed previously!
pip install rdflib==4.1.2
pip install -r pip-requirements.txt
pip install -r pip-requirements-dev.txt
pip install -r pip-requirements-local.txt
# shared assets is not python, so we can't pip install it
git clone https://github.com/datagovuk/shared_dguk_assets.git

echo "Node install..."
sudo apt-get install python-software-properties python g++ make
sudo add-apt-repository -y ppa:chris-lea/node.js
sudo apt-get update
sudo apt-get install nodejs
sudo npm install -g grunt-cli
npm install
cd shared_dguk_assets
npm install
cd -

echo "Download nltk stopwords..."
python -m nltk.downloader stopwords

echo "Asset compilation (grunt)..."
grunt
cd shared_dguk_assets
grunt
cd -

echo "Moving test-core.ini into a subdir..."
# because it expects to find ckan's test-core.ini in a sister directory of
# ckanext-dgu but on travis it is in a sub-directory
mkdir subdir
mv test-core.ini subdir
# put resource_formats.json where the newly moved test-core.ini can find it
mkdir subdir/config
mv config/resource_formats.json subdir/config/resource_formats.json

# Copy who.ini into the subdir
mkdir -p subdir/ckanext/dgu
cp ckanext/dgu/who.ini subdir/ckanext/dgu/

echo "travis-build.bash is done."
