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

echo "Installing ckanext-dgu and its requirements..."
python setup.py develop
# seems like ckanext-taxonomy dependency 'python-skos' won't even start
# installing without rdflib already being installed previously!
pip install rdflib==4.1.2
pip install -r pip-requirements.txt
pip install -r pip-requirements-dev.txt
pip install -r pip-requirements-local.txt

echo "Moving test-core.ini into a subdir..."
mkdir subdir
mv test-core.ini subdir

# Copy who.ini into the subdir
mkdir -p subdir/ckanext/dgu
cp ckanext/dgu/who.ini subdir/ckanext/dgu/

echo "travis-build.bash is done."
