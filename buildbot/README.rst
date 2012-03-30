dgu-buildbot.okfn.org
*********************

An instance of Jenkins installed on dgu-buildbot.okfn.org is used to build the
CKAN apt packages and to deploy to releasetest.ckan.org

Deployment Process
==================

1. Log onto jenkins.ckan.org
#. Build the CKAN package (optional)

   i)   Select *Package A CKAN Branch* from the main table.
   ii)  Select *Build Now* from the menu on the left.
   iii) Fill out the form, and click *Build*

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

   i)   Select *Create a DGU Instance* from the main table on the home page.

   ii)  Select *Build Now* from the menu on the left.

   iii) Fill out the form, and click "Build*

        repo_name
          This is the name of the CKAN repository to use to install CKAN from.
          ie - it should match the repo_name argument given in the *Package A
          CKAN Branch* instructions. eg. ``ckan-dev`` or ``ckan-1.6.1``.

        dgu_branch
          This is the branch in *ckanext-dgu* repo to use as the basis for the
          release.  eg. ``master``, ``v1.0-dev`` or ``bigbang``.

  vi)   Conosle output can be seen by clicking on the new build in the *Build
        History* menu on the left, and then clicking *Console Output* in the
        menu on the left.  The build will take quite a while to run (26 minutes
        at the last count).  Mostly due to database migrations.

  v)    Log on to releasetest by first logging into dgu-buildbot.okfn.org, and
        then from there, ssh-ing into ``ubuntu@192.168.100.100``.

#. Install postfix mail server on the new VM.  It isn't installed when the VM
   is created as it's an interactive installation.

   i)   Log into the new VM: ``ssh ubuntu@192.168.100.100``.

   ii)  Install postfix: ``sudo apt-get install postfix``.  Follow
        instructions, select ``Internet Site`` at the *Postfix Configuration*.
        And ``releasetest.ckan.org`` for the *Sytem Mail Name*.

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

1.  Jenkins executes the script ``/home/okfn/create-dgu-instance-wrapper.sh``.
    I can't remember the reasoning behind this wrapper, in that all it does is 


