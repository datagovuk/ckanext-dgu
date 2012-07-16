dgu-buildbot.okfn.org
*********************

An instance of Jenkins installed on dgu-buildbot.okfn.org is used to build the
CKAN apt packages and to deploy to releasetest.ckan.org

Deployment Process
==================

#. Build the CKAN package (optional)

   i)   Log onto CKAN's jenkins: s031.okserver.org:8080
   ii)  Select *Package_CKAN* from the main table.
   iii) Select *Build Now* from the menu on the left.
   iv)  Fill out the form, and click *Build*

        branch_name
          The name of the branch in the repository that should be built, eg.
          ``master`` or ``release-v1.6.1``.

        repo_name
          The name of the release, eg. ``ckan-dev`` or ``ckan-1.6.1``.  This
          value determines the repo name, so it will be published on
          apt.ckan.org as ``apt.ckan.org/ckan-1.6.1`` for example.  At the
          moment (as of 29th March 2012) we're using the 1.6.1
          release-candidate ``ckan-1.6.1-rc``.

        ckan_package_version
          If you've already built CKAN for the above repo_name, then this
          allows you bump the version.  Auto-increment this on each build for a
          given repo_name.

        deps_package_version
          Set this to the same as the ckan_package_version.

   iv)  You can view the output by clicking on *Console Output* in the menu on
        the left.

#. Create a new DGU instance

   i)   Log onto jenkins.ckan.org
   ii)  Select *Create a DGU Instance* from the main table on the home page.

   iii) Select *Build Now* from the menu on the left.

   iv)  Fill out the form, and click "Build*

        repo_name
          This is the name of the CKAN repository to use to install CKAN from.
          ie - it should match the repo_name argument given in the *Package A
          CKAN Branch* instructions. eg. ``ckan-dev`` or ``ckan-1.6.1``.

        dgu_branch
          This is the branch in *ckanext-dgu* repo to use as the basis for the
          release.  eg. ``master``, ``v1.0-dev`` or ``bigbang``.

   v)   Conosle output can be seen by clicking on the new build in the *Build
        History* menu on the left, and then clicking *Console Output* in the
        menu on the left.  The build will take quite a while to run (26 minutes
        at the last count).  Mostly due to database migrations.

   vi)  Log on to releasetest by first logging into dgu-buildbot.okfn.org, and
        then from there, ssh-ing into ``ubuntu@192.168.100.100``.

#. Install postfix mail server on the new VM.  It isn't installed when the VM
   is created as it's an interactive installation.

   i)   Log into the new VM: ``ssh ubuntu@192.168.100.100``.

   ii)  Install postfix: ``sudo apt-get install postfix``.  Follow
        instructions, select ``Internet Site`` at the *Postfix Configuration*.
        And ``releasetest.ckan.org`` for the *Sytem Mail Name*.

Things that have gone wrong in the past
---------------------------------------

File size mis-match
...................

Presented with the following error messages: ::

  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-pyutilib.component.core/python-pyutilib.component.core_4.1+01+lucid-1_all.deb  Size mismatch
  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-vdm/python-vdm_0.10+01+lucid-1_all.deb  Size mismatch
  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-autoneg/python-autoneg_0.5+01+lucid-1_all.deb  Hash Sum mismatch
  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-formalchemy/python-formalchemy_1.4.1+01+lucid-1_all.deb  Size mismatch
  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-pairtree/python-pairtree_0.7.1-T+01+lucid-1_all.deb  Size mismatch
  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-ofs/python-ofs_0.4.1+01+lucid-1_all.deb  Size mismatch
  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-apachemiddleware/python-apachemiddleware_0.1.1+01+lucid-1_all.deb  Size mismatch
  Failed to fetch http://apt.ckan.org/ckan-1.6.1-rc/pool/universe/p/python-markupsafe/python-markupsafe_0.9.2+01+lucid-1_all.deb  Size mismatch
  E: Unable to fetch some archives, maybe run apt-get update or try with --fix-missing?

When migrating apt.ckan.org from dgu-buildbot, and then deploying to
releasetest, apt-get failed to install ckan as there was a mis-match between
the file size recorded in the metadata, and that of the actual packages.  It
turns out, there's an apt-cacher running on dgu-buildbot.  The cached files can
be found in ``/var/cache/apt-cacher-ng``.  To fix the issue I removed the
cached ``apt.ckan.org`` directory.

Checking the deployment
-----------------------

There's no suite of tests to run to check that the deployment has worked, but
some common things to check are:

* The dataset count on the homepage should steadily increase to >8000 whilst
  the search index is being populated.  If this isn't happening, then the
  search-index hasn't been started.  Look in the output console on Jenkins, and
  `search_index_log`_ on the VM.

* The datasets should have publishers associated with them.  If not, then
  something will have gone wrong with the migration.  Again, check the console
  output in Jenkins.  Also, `migration_errors_log`_ indicates migration
  problems.  If the problem seems to only with UKLP datasets, then check that
  the harvester has started.  The console output should show that the
  fetcher and gatherers have been started, and there's a log file at
  `harvest_log`_ on the VM.

* Check the qa background tasks were started: the
  `dashboard <http://releasetest.ckan.org/qa>`_ should show that some links have
  been checked.

* Not all UKLP datasets have Providers, but there should be *some*.  If
  datasets with Providers is looking sparse, then that's an indication that the
  harvest hasn't run properly.  Check the `harvest_log`_.

Useful log files
................

.. _harvest_log:
.. _search_index_log:
.. _qa_log:
.. _migration_errors_log:

The following logs are created by some of the various scripts that run during
the deployment:

/home/ubuntu/**errors.csv**
  Errors that occurred during association of publisher and datasets.

/home/ubuntu/**harvester_output.log**
  The output from running the ``harvest import`` command.

/home/ubuntu/**qa_output.log**
  The output from running the ``qa update`` command.

/home/ubuntu/**solr_output.log**
  The output from running the ``search-index rebuild`` command.

.. _logs:

Other standard CKAN logs are found in the usual places, ie -
``/var/log/apache2//``, ``/var/log/ckan/std/``, ``/var/log/rabbitmq/``,
``/var/log/jetty/``

Technical Overview
==================

This section describes what happens during the deployment, which scripts are
responsible for what and where they're found.

Architecture
------------

DGU deployements run as KVMs on dgu-buildbot.okfn.org.  The VM runs a standard
package install of CKAN, and source installs of the various extensions, running
inside a python virtualenv.  An nginx service is running on
dgu-buildbot.okfn.org which forwards http requests to releasetest.ckan.org onto
192.168.100.100 (the IP address of the VM).

Overview
--------

When deploying to releasetest, the old VM is torn down, and a new one is
started from a fixed hard drive image.  Various files are copied across onto
the new VM, including an installation script.  This installation script is then
executed on the new VM when it has booted.  The management of VMs is handled by
buildkit.

The install script(s) first copy the latest dump of the DGU database onto the
VM, and then execute a script which:

1. Installs CKAN and its dependencies from apt.ckan.org
#. Installs DGU and its dependencies
#. Restores the database from the dump, and runs migrations defined in
   ckanext-dgu.
#. Configures the installation (edits ``/etc/ckan/std/std.ini``).
#. Creates a test admin user
#. Runs post-installation instructions defined in ckanext-dgu
#. Restarts apache.
#. Starts some background tasks
   * rebuilding the search index
   * starting the harvest import
   * starting the qa update

There are various stages to this process, with control being delegated to a
number of different scripts at different stages (detailed in the next section).

Process in detail
-----------------

Jenkins
.......

Jenkins calls ``/home/okfn/create-dgu-instance-wrapper.sh``.  The arguments are
the repo name and the dgu branch to deploy.  After which the rest of the
process is controller by the various scripts described below...

create-dgu-instance.sh
......................

``/home/okfn/create-dgu-instance.sh`` is called with the CKAN repo name (eg -
``ckan-1.6.1``) and the branch on ckanext-dgu to deploy (eg - ``v1.0-dev``).

This script uses buildkit to tear down the old VM, and boot a new one in its
place.  The new image is based on an archived image found at
``/var/lib/buildkit/vm/base.qcow2``.  As part of the creation of the VM,
buildkit copies a number of files onto the new VM:

/home/okfn/.ssh/dgu-buildbot.okfn.org_rsa
  This is the private key of the ``dgu-buildbot`` account on bitbucket.  This
  user has read access to the ckanext-os extension, and is used in order that
  that extension can installed on the new VM.

  It's copied to the home of the ckanstd user.

/home/buildslave/dumps/latest.pg_dump
  This is a copy of the latest dump of data from the *CKAN* database on DGU.

/home/buildslave/dumps/users.csv
  This is a copy of the users found on the *Drupal* database on DGU.  It's not
  generated from the latest backup, so will gradually become more out of date.
  Although fine for releasetest, this file will obviously need updating for the
  final production deployemnt.

/home/okfn/new/install_dgu.sh
  This is the base script for installing CKAN and DGU on the VM.  It's copied
  over onto the VM, and later invoked over ssh (using fabric).

vm-fabfile.py
.............

This is just a simple fab file.  The only function that's used is
``install_dgu``, which just executes the script that was copied across when
creating the new VM (see `create-dgu-instance`_).

install_dgu.sh
..............

This script lives on dgu-buildbot.okfn.org: ``/home/okfn/new/install_dgu.sh``.
It's copied across to the VM upon creation.

It's purpose is to install CKAN; CKAN's dependencies; DGU; restore the database
and run migrations; configure the DGU installation; and run some
post-installation scripts.

One thing to note about this script, is that it uses ``source`` to pull in
further functionality from the script named ``install_dgu_instance``, found in
the ckanext-dgu repository: ``ckanext-dgu/buildbot/instance_dgu_instance.sh``.
This second script allows each dgu branch to customise the installation.  For
example, different branches may need different plugins, or run different
migrations.

The last thing this script does to is to start some background processes:

* Rebuilding the search index.
* Starting the harvest import.
* Starting the QA update.

Another thing to note is that although there's a copy of ``install_dgu.sh`` in
the ckanext-dgu repository (``ckanext-dgu/buildbot/jenkins/install_dgu.sh``),
it is for archive purposes only.  And **changing in the repo will not affect
the build**. (Unlike ``ckanext-du/buildbot/install_dgu_instance.sh``, which
**will** affect the build if changed in the repo).

install_dgu_instance.sh
.......................

This script lives in the ckanext-dgu repository, and it implements a number of
functions which act as hooks into the above `install_dgu.sh`_ script.

install_dependencies()
  Called by the ``install_dgu()`` function.  This is called immediately after
  ckanext-dgu has been checked out and installed in the virtualenv.

run_database_migrations()
  Called by ``restore_database()`` once the database has been restored and is
  ready by for use.  It's an optional hook.

configure()
  Called by ``configure_ini_file()`` after the migrations have run.  Use this
  to add various options to the .ini file.

post_install()
  Called once the installation is complete, after the deployment
  is configured,just before apache is restarted.  This is an option hook.


