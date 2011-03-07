CKAN Installation for DGU
+++++++++++++++++++++++++

As root...

::

If running apache, ensure this apache module is installed:

::

    apt-get install libapache2-mod-wsgi

Add a new user called ``okfn``:

::

    useradd -d /home/okfn -m okfn


Edit ``/etc/apt/sources.list`` and add this at the top:

::

    # CKAN
    deb http://apt-alpha.ckan.org/debian lucid universe

Then add the key we need:

::

    sudo apt-get install curl
    curl -o packages.okfn.key http://apt-alpha.ckan.org/packages.okfn.key
    apt-key add packages.okfn.key

Now install CKAN DGU:

::

    apt-get update
    apt-get install python-ckanext-dgu
    apt-get install python-apachemiddleware

Here's the output you'll see:

::

    root@coi-ckan-dev1:~#     apt-get install python-ckanext-dgu
    Reading package lists... Done
    Building dependency tree       
    Reading state information... Done
    The following extra packages will be installed:
      javascript-common libjpeg62 libjs-jquery libjs-prototype
      libjs-scriptaculous liblcms1 libpaper-utils libpaper1 libpq5 libxslt1.1
      python-beaker python-beautifulsoup python-cheetah python-ckan
      python-ckan-deps python-ckanclient python-decorator python-docutils
      python-egenix-mxdatetime python-egenix-mxtools python-formalchemy
      python-formencode python-imaging python-jinja2 python-ldap python-licenses
      python-lxml python-mako python-markupsafe python-nose python-openid
      python-openssl python-paste python-pastedeploy python-pastescript
      python-pkg-resources python-psycopg2 python-pygments python-pylons
      python-pyutilib.component.core python-repoze.who python-repoze.who-plugins
      python-roman python-routes python-scgi python-simplejson python-sphinx
      python-sqlalchemy python-support python-tempita python-vdm python-weberror
      python-webhelpers python-webob python-webtest python-zope.interface
      wwwconfig-common
    Suggested packages:
      liblcms-utils texlive-latex-recommended texlive-latex-base
      texlive-lang-french python-egenix-mxdatetime-dbg python-egenix-mxtools-dbg
      python-egenix-mxtools-doc python-dns python-imaging-doc python-imaging-dbg
      python-jinja2-doc python-ldap-doc python-lxml-dbg python-coverage
      python-openssl-doc python-openssl-dbg python-pastewebkit
      libapache2-mod-wsgi libapache2-mod-python libapache2-mod-scgi python-pgsql
      libjs-mochikit python-cherrypy3 python-cherrypy python-flup
      python-distribute python-distribute-doc python-chardet python-jinja
      python-genshi python-kid python-turbokid python-myghty python-pudge ipython
      python-migrate jsmath python-sqlalchemy-doc python-mysqldb
      python-kinterbasdb python-pymssql python-z3c.recipe.sphinxdoc
      postgresql-client apache apache-ssl
    The following NEW packages will be installed
      javascript-common libjpeg62 libjs-jquery libjs-prototype
      libjs-scriptaculous liblcms1 libpaper-utils libpaper1 libpq5 libxslt1.1
      python-beaker python-beautifulsoup python-cheetah python-ckan
      python-ckan-deps python-ckanclient python-ckanext-dgu python-decorator
      python-docutils python-egenix-mxdatetime python-egenix-mxtools
      python-formalchemy python-formencode python-imaging python-jinja2
      python-ldap python-licenses python-lxml python-mako python-markupsafe
      python-nose python-openid python-openssl python-paste python-pastedeploy
      python-pastescript python-pkg-resources python-psycopg2 python-pygments
      python-pylons python-pyutilib.component.core python-repoze.who
      python-repoze.who-plugins python-roman python-routes python-scgi
      python-simplejson python-sphinx python-sqlalchemy python-support
      python-tempita python-vdm python-weberror python-webhelpers python-webob
      python-webtest python-zope.interface wwwconfig-common
    0 upgraded, 58 newly installed, 0 to remove and 0 not upgraded.
    Need to get 11.8MB of archives.
    After this operation, 71.3MB of additional disk space will be used.
    Do you want to continue [Y/n]? 

You'll need PostgreSQL too:

::

    apt-get install postgresql

Now you can create your configuration, set up the database and serve your CKAN instance. No virtual environments required!

    
    sudo -u postgres createuser -S -D -R -P dgu
    # Enter password `pass' or you'll need to edit your config with the new settings
    sudo -u postgres createdb -O dgu dgu

Now set up the ckan server:

::
    (see nils for mkdir cmds)
    $ paster make-config ckan /etc/ckan/dgu/dgu.ini
    Distribution already installed:
      ckan 1.4a from /usr/lib/pymodules/python2.6
    Creating /etc/ckan/dgu/dgu.ini
    Now you should edit the config files
      /etc/ckan/dgu/dgu.ini

Now edit ``/etc/ckan/dgu/dgu.ini`` as follows:

::

    email_to = ckan-sysadmin@okfn.org
    error_email_from = no-reply@dgu-dev.ckan.net


Add to the ``[app:main]`` section the following:

::

    ckan.plugins = dgu_form_api
    dgu.xmlrpc_username = CKAN_API
    dgu.xmlrpc_password = XXXX
    dgu.xmlrpc_domain = 212.110.177.166
    ckan.log_dir = /var/log/ckan/dgu
    ckan.dump_dir = /var/lib/ckan/dgu/static/dump
    ckan.backup_dir = /var/backup/ckan/dgu


and change these lines:

::

    package_form = package_gov3
    sqlalchemy.url = postgresql://ckantest:pass@localhost/ckantest
    cache_dir = /var/lib/ckan/dgu/data
    ckan.site_title = DGU dev

You also need the who.ini:

::

    curl -o /etc/ckan/dgu/who.ini https://bitbucket.org/okfn/ckan/raw/dc64fe524be5/who.ini 

Edit the who.ini:

::

    store_file_path = /var/lib/ckan/dgu/sstore

Now set file permissions:

::
    (see nils)

Now you can create either a new database:

::

    paster --plugin=ckan db init --config=/etc/ckan/dgu/dgu.ini

Or restore a database dump:

::

    psql -W -U dgu -d dgu -h localhost -f hmg.ckan.net.current.2011-03-02.pg_dump
    # it will prompt for the db user password ('pass' was the default)
    paster --plugin=ckan db upgrade --config /etc/ckan/dgu/dgu.ini

Now try serving the app:

::

    sudo -u www-data paster serve /etc/ckan/dgu/dgu.ini

In another shell on the machine:

::
    curl http://127.0.0.1:5000

Now create the /etc/ckan/dgu.py:

::

  import os
  from apachemiddleware import MaintenanceResponse

  config_filepath = '/etc/ckan/dgu/dgu.ini'

  # logging
  from paste.script.util.logging_config import fileConfig
  fileConfig(config_filepath)

  from paste.deploy import loadapp
  application = loadapp('config:%s' % config_filepath)
  application = MaintenanceResponse(application)

And create the apache config /etc/apache2/sites-available/dgu:

::

  <VirtualHost *:80>
    DocumentRoot /var/lib/ckan/static
    ServerName dgu

    <Directory /var/lib/ckan/static>
        allow from all
    </Directory>

    Alias /dump /var/lib/ckan/static/dump

    # Disable the mod_python handler for static files
    <Location /dump>
        SetHandler None
        Options +Indexes
    </Location>

    # this is our app
    WSGIScriptAlias / /etc/ckan/dgu.py

    # pass authorization info on (needed for rest api)
    WSGIPassAuthorization On

   # Basic auth
   #<Location />
   #     AuthType Basic
   #     AuthName "data.gov.uk CKAN Replica"
   #     AuthUserFile /etc/ckan/hmg.ckan.net.passwd
   #     AuthGroupFile /etc/ckan/hmg.ckan.net.groups
   #     Require group okfn
        ## START - Allow unauthenticated local access.
   #     Order allow,deny
   #     Allow from 127.0.0.1
        #  Allow from 10.254.209.254 # hmgqueue
        ## disable write operations except for explicitly
        ## allowed hosts
        #   <Limit PUT POST DELETE>
        #       Order deny,allow
        #       Allow from 127.0.0.1
        #       Allow from 10.254.209.254 # hmgqueue
        #       Deny from all
        #   </Limit>
   #     Satisfy any
        ## END - Allow unauthenticated local access.
   # </Location>

        ErrorLog /var/log/apache2/dgu.error.log
        CustomLog /var/log/apache2/dgu.custom.log combined
  </VirtualHost>

Now restart apache:

::

    sudo /etc/init.d/apache2 restart


Cron jobs
=========

Install the gov-daily.py and ONS crons (TODO)


Building debian package
=======================

This is the command I used to build the deb:

::

    python -m buildkit.deb missing ckanext-dgu 1.3 http://ckan.org python-ckan

Then set up the API key:

::

    paster --plugin=ckan shell --config=/etc/ckan/dgu/dgu.ini

Then paste in this and press Ctrl+D:

::

    from ckan import model
    from ckan.model.meta import Session
    Session.add(model.User(name='frontend2', apikey='26ee09f5-fc47-4359-92b4-b48fd6ba78b3', about='Drupal Dev Instance'))
    Session.commit()