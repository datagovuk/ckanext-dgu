
1. Install CKAN

    pip install -e  hg+https://bitbucket.org/okfn/ckan#egg=ckan


2. Install ckanext-harvest
    
    * The extension uses rabbitMQ as messaging system. Install it with::
    
        sudo apt-get install rabbitmq-server

    * Install the extension::
    
        pip install -e  hg+https://bitbucket.org/okfn/ckanext-harvest#egg=ckanext-harvest

    * Run the following command to create the necessary tables::
    
        paster harvester initdb --config=../ckan/development.ini
                    
    * Add the following plugins to the ckan ini file::

        ckan.plugins = harvest

    * The extension needs a user with sysadmin privileges to perform the 
      harvesting jobs (Only while it uses the DGU forms interface). 
      You can create such a user running these two commands in
      the ckan directory::

        paster user add harvest

        paster sysadmin add harvest

    * The user's API key must be defined in the CKAN
      configuration file (.ini) in the [app:main] section::

        ckan.harvest.api_key = 4e1dac58-f642-4e54-bbc4-3ea262271fe2

    * The API URL used can be also defined in the ini file (it defaults to 
      http://localhost:5000/)::

        ckan.api_url = <api_url>


3. Install ckanext-csw

    * Install the extension::
    
        pip install -e  hg+https://bitbucket.org/okfn/ckanext-csw#egg=ckanext-csw

    
    * Add the following plugins to the ckan ini file::

        ckan.plugins = cswserver
    
    
4. Install ckanext-dgu

    * Install the extension::

        pip install -e  hg+https://bitbucket.org/okfn/ckanext-dgu#egg=ckanext-dgu

    
    * Add the following plugins to the ckan ini file::

        ckan.plugins = dgu_form_api
    

5. Install ckanext-inspire

    * Install the extension::

        pip install -e  hg+https://bitbucket.org/okfn/ckanext-inspire#egg=ckanext-inspire

    
    * Add the following plugins to the ckan ini file::

        ckan.plugins = gemini_harvester gemini_doc_harvester gemini_waf_harvester inspire_api
    
    
6. Install ckanext-spatial
    
    * Install the extension::
    
        pip install -e  hg+https://bitbucket.org/okfn/ckanext-spatial#egg=ckanext-spatial
    
    
    * To use the spatial search you need to install and configure PostGIS::

        sudo apt-get install postgresql-8.4-postgis

        sudo -u postgres createdb [database]
        sudo -u postgres createlang plpgsql [database]
        sudo -u postgres psql -d [database] -f /usr/share/postgresql/8.4/contrib/postgis-1.5/postgis.sql
        sudo -u postgres psql -d [database] -f /usr/share/postgresql/8.4/contrib/postgis-1.5/spatial_ref_sys.sql
        sudo -u postgres psql -d [database] -c "ALTER TABLE geometry_columns OWNER TO [db_user]"    
        sudo -u postgres psql -d [database] -c "ALTER TABLE spatial_ref_sys OWNER TO [db_user]"
        
        The following command should output the PostGIS version::
    
        sudo -u postgres psql -d [database] -c "SELECT postgis_full_version()"
    
    
    * Run the following command to create the necessary tables::
    
        paster spatial initdb --config=../ckan/development.ini
        
        Problems you may find::
    
            LINE 1: SELECT AddGeometryColumn('package_extent','the_geom', E'4258...
                   ^
            HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
             "SELECT AddGeometryColumn('package_extent','the_geom', %s, 'POLYGON', 2)" ('4258',)

        PostGIS was not installed correctly. Please check the previous step.
        
        
            sqlalchemy.exc.ProgrammingError: (ProgrammingError) permission denied for relation spatial_ref_sys
        
        The user accessing the ckan database needs to be owner (or have 
        permissions) of the geometry_columns and spatial_ref_sys tables::
            
                ALTER TABLE geometry_columns OWNER TO ckantest
                ALTER TABLE spatial_ref_sys OWNER TO ckantest
        
   
   
    * Add the following plugins to the ckan ini file::

        ckan.plugins = wms_preview spatial_query
        
        
    * Add the following configuration options in the ckan ini file::

        ckan.spatial.srid = 4258


