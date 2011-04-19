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

You need to enable apache `rewrite`::

    $ sudo a2enmod rewrite

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
    ckan.site_url = http://dgu-dev.okfn.org
    ckan.default_roles.Package = {"visitor": ["reader"], "logged_in": ["reader"]}
    ckan.default_roles.Group = {"visitor": ["reader"], "logged_in": ["reader"]}
    ckan.default_roles.System = {"visitor": ["reader"], "logged_in": ["reader"]}
    ckan.default_roles.AuthorizationGroup = {"visitor": ["reader"], "logged_in": ["reader"]}
    licenses_group_url = http://licenses.opendefinition.org/2.0/ukgov

Also, in the loggers section:

::

    [loggers]
    keys = root, ckan, ckanext

    [handlers]
    keys = console, file

    ...

    [logger_root]
    level = WARNING
    handlers = file

    ...

    args = ('/var/log/ckan/dgu/dgu.log', 'a', 2000000, 9)

Now copy the config to a maintenance mode version::

    $ sudo cp /etc/apache2/sites-available/dgu /etc/apache2/sites-available/dgu.maintenance

and insert these lines just before the WSGIScriptAlias line::

    RewriteEngine On
    RewriteRule ^(.*)/new /return_503 [PT,L]
    RewriteRule ^(.*)/create /return_503 [PT,L]      
    RewriteRule ^(.*)/authz /return_503 [PT,L]
    RewriteRule ^(.*)/edit /return_503 [PT,L]
    RewriteCond %{REQUEST_METHOD} !^GET$ [NC]
    RewriteRule (.*) /return_503 [PT,L]


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

Now create the link to the wsgi script

Find this script's installed path::

    $ python -c 'from ckanext.dgu import bin; print bin.__path__'
    ['/usr/lib/pymodules/python2.6/ckanext/dgu/bin']
  
Create symlink::

    ln -s /usr/lib/pymodules/python2.6/ckanext/dgu/bin/wsgi.py /etc/ckan/dgu/dgu.py

Now create the apache config /etc/apache2/sites-available/dgu:

::

  <VirtualHost *:80>
    DocumentRoot /var/lib/ckan/dgu/static
    ServerName dgu-dev.okfn.org
    ServerAlias *

    <Directory /var/lib/ckan/dgu/static>
        allow from all
    </Directory>

    Alias /dump /var/lib/ckan/dgu/static/dump

    # Disable the mod_python handler for static files
    <Location /dump>
        SetHandler None
        Options +Indexes
    </Location>

    # this is our app
    WSGIScriptAlias / /etc/ckan/dgu/dgu.py

    # pass authorization info on (needed for rest api)
    WSGIPassAuthorization On

   # Basic auth
   #<Location />
   #     AuthType Basic
   #     AuthName "data.gov.uk CKAN Replica"
   #     AuthUserFile /etc/ckan/dgu/dgu.passwd
   #     AuthGroupFile /etc/ckan/dgu/dgu.groups
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

Enable right apache config:

::

    sudo a2dissite 000-default
    sudo a2ensite dgu

Now restart apache:

::

    sudo /etc/init.d/apache2 restart


Cron jobs
=========

Install the harvester, gov-daily.py (dump and backup) and ONS (TODO) cron jobs:

::

    $ sudo -u ckan crontab -e

    # m h  dom mon dow   command
    */10 *   * * * paster --plugin=ckan harvester run --config=/etc/ckan/dgu/dgu.ini
    30 23    * * *  python /usr/lib/pymodules/python2.6/ckanext/dgu/bin/gov-daily.py /etc/ckan/dgu/dgu.ini



Locking down a database
======================

When taking the database from hmg.ckan.net, because the new servers are open, the permissions of the packages and the system need to be tightened up to prevent editing unless you are a sysadmin:

::

    paster --plugin=ckan rights remove logged_in editor package:all --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights remove visitor editor package:all --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights make logged_in reader package:all --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights make visitor reader package:all --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights remove logged_in editor system --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights make logged_in reader system --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights remove visitor reader system --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights remove frontend2 admin package:all --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan sysadmin add okfn --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan sysadmin add hmg --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan sysadmin add team --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan sysadmin add tna --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan sysadmin add autoload --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan sysadmin add frontend3 --config=/etc/ckan/dgu/dgu.ini
    paster --plugin ckan roles --config /etc/ckan/dgu/dgu.ini deny reader create
    paster --plugin ckan roles --config /etc/ckan/dgu/dgu.ini deny reader create-package

Ensure you have an okfn_maintenance user::

    paster --plugin=ckan user add okfn_maintenance --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan sysadmin add okfn_maintenance --config=/etc/ckan/dgu/dgu.ini

And after upgrate of migration 36::

    paster --plugin=ckan rights remove visitor anon_editor system --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan rights make visitor reader system: --config=/etc/ckan/dgu/dgu.ini
    paster --plugin=ckan roles deny reader create-package --config=/etc/ckan/dgu/dgu.ini

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
    Session.add(model.User(name='frontend2', apikey=XXX, about='Drupal Dev Instance'))
    Session.commit()