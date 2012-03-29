dgu-buildbot.okfn.org
*********************

An instance of Jenkins installed on dgu-buildbot.okfn.org is used to build the
CKAN apt packages and to deploy  to releasetest.ckan.org

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
        menu on the left.  The build will take quite a while to run.  Mostly
        due to database migrations.

  v)    Log on to releasetest by first logging into dgu-buildbot.okfn.org, and
        then from there, ssh-ing into ``ubuntu@192.168.100.100``.

#. Install postfix mail server on the new VM.  It isn't installed when the VM
   is created as it's an interactive installation.

   i)   Log into the new VM: ``ssh ubuntu@192.168.100.100``.

   ii)  Install postfix: ``sudo apt-get install postfix``.  Follow
        instructions, select *Web Server*.
