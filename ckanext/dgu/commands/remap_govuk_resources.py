# -*- coding: utf-8 -*-
# This command takes the remappings performed by GDS in https://github.com/alphagov/redirector
# and checks each of the local resources to see if they need to be changed.
# When a 301 (or 418 - sigh) is found then the url to the resource is updated.
# When a 410 is found then the resource is deleted, should the dataset then contain no resources
# then that is also deleted.
# A log file of the changes will be written to remap.log

import os
import csv
import sys
import glob
import datetime
import locale
import logging
import resource
import subprocess
import collections
from ckan.lib.cli import CkanCommand
from ckanext.dgu.bin.running_stats import StatsCount

log = logging.getLogger("ckanext")

# Creates a log of the work we have done, contains the package and its new state,
# the resource and its new state, and the action taken.  The action can be one of
# Changed, ResourceDeleted, or PackageDeleted
TRANSLOG_CHANGED          = "Changed"
TRANSLOG_RESOURCE_DELETED = "Resource deleted"
TRANSLOG_PACKAGE_DELETED  = "Package deleted"
TRANSLOG_PACKAGE_ALREADY_DELETED  = "Package already deleted"

translog = csv.writer(open("remap.log", "wb"))
translog.writerow(["PackageName", "PackageState", "ResourceID", "ResourceState", "Action"])

GIT_REPO = "https://github.com/alphagov/redirector.git"


class ResourceRemapper(CkanCommand):
    """
    Iterates through resources to checks if it was remapped by gov.uk.  

    If the status is 301, then we will modify the URL of the resource, keeping track
    of the # of changes we made.  If a 410 we'll delete the resource, and if it was the
    only resource, we'll delete the dataset as well.
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(ResourceRemapper, self).__init__(name)
        self.parser.add_option("-n", "--nopull",
                  dest="nopull", action="store_true",
                  help="Specifies the the code should not pull the latest version if the repo exists on disk")
        self.parser.add_option("-p", "--pretend",
                  dest="pretend", action="store_true",
                  help="Pretends to update the database, but doesn't really.")        
        self.local_resource_map = collections.defaultdict(list)
        self.remap_stats = StatsCount()

    def record_transaction(self, package, resource, action):
        """ Write a record to the log file """
        row = [package.name, package.state, resource.id, resource.state, action]
        translog.writerow(row)

    def _rss(self):
        """ Return a string containing how much memory we're currently using """
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024                
        locale.setlocale(locale.LC_ALL, 'en_GB')
        return locale.format('%d', rss, grouping=True) + "Mb"
                

    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")
        log.debug("MEM: {0}".format(self._rss()))

        # Clone/pull the info from the git repo
        data_folder = self._get_remapping_data()
        self._build_local_resource_map()
        log.debug("MEM: {0}".format(self._rss()))

        log.debug("Looking for CSV files in {0}".format(data_folder))

        # Iterate through all of the CSV files in the repository
        iterator = glob.iglob(os.path.join(data_folder, "*.csv"))
        for csv_file in iterator:
            self.remap_stats.increment('CSV files read')    

            with open(csv_file, "rU") as f:
                rdr = csv.reader(f)
                rdr.next() # Skip the header

                for row in rdr:
                    if row[0] in self.local_resource_map:
                        self.remap_stats.increment('URLs matched')
                
                        # Each URL in our local map might appear more than once, so 
                        # the list of resource IDs it iterated over
                        for resource_id in self.local_resource_map[row[0]]:
                            resource = model.Session.query(model.Resource).\
                                filter(model.Resource.id==resource_id).first()

                            if resource == None:
                                log.error("Resource {0} is not findable".format(resource_id))

                            # Depending on the HTTP code registered for the remap we should
                            # either treat it as gone, or as a simple move.
                            code = int(row[2])
                            if code == 410:
                                self.handle_gone(row, resource)
                            elif code in [301, 418]:
                                self.handle_moved(row, resource)

                    self.remap_stats.increment('Rows read')

        print self.remap_stats.report(order_by_title=True)

    def handle_gone(self, row, resource):
        """ 
            Marks the resource as deleted, and then checks if there are no more 
            resources in the package. it will delete the dataset too if there are no
            other resources 
        """
        import ckan.model as model

        resource.state = 'deleted' 
        if not self.options.pretend:
            model.Session.add(resource)
            model.Session.commit()

        pkg = resource.resource_group.package
        if pkg.state == 'deleted':
            self.remap_stats.increment('URL has GONE within already deleted package')
            self.record_transaction(pkg, resource, TRANSLOG_PACKAGE_ALREADY_DELETED)
            return 

        if self._should_delete(pkg, resource):
            if not self.options.pretend:
                pkg.state == 'deleted'
                model.Session.add(pkg)
                model.Session.commit()
            self.remap_stats.increment('Packages deleted due to 0 resources')
            self.record_transaction(pkg, resource, TRANSLOG_PACKAGE_DELETED)
        else:
            self.record_transaction(pkg, resource, TRANSLOG_RESOURCE_DELETED)            
        
        self.remap_stats.increment('410 GONE')

    def handle_moved(self, row, resource):
        """ 
            Changes the url in the resource to the new one
        """
        import ckan.model as model

        # Alays assign the URL, regardless of the state of the package just so that
        # it is clean (should it be un-deleted)
        resource.url = row[1]       
        if not self.options.pretend:
            model.Session.add(resource)
            model.Session.commit()        

        # Record whether we have updated an active resource within a deleted package
        pkg = resource.resource_group.package
        if pkg.state == 'deleted':
            self.remap_stats.increment('URL has MOVED within already deleted package')
            self.record_transaction(pkg, resource, TRANSLOG_PACKAGE_ALREADY_DELETED)
            return

        self.record_transaction(pkg, resource, TRANSLOG_CHANGED)            
        self.remap_stats.increment('301 MOVED')

    def _should_delete(self, pkg, resource):
        # Should we delete the specified package when there is one less active resource?
        any_left = any([r.id for r in pkg.resources if r.state == 'active' and r.id != resource.id])
        return not any_left

    def _build_local_resource_map(self):
        """ 
        Builds a map of the resources we know about locally that we will store with the URL
        as the key, and the value as a list of resource ids that have this URL """
        import ckan.model as model

        log.debug("Building local resource map")
        q = model.Session.query(model.Resource)\
            .filter(model.Resource.state=='active')
        for resource in q.all():
            self.local_resource_map[resource.url].append(resource.id)
        log.debug("Local resource map contains {0} elements".format(len(self.local_resource_map)))


    def _run_or_exit(self, cmd, error_message):
        """ Runs the specified command, and exits with an error if it fails """
        err = subprocess.call(cmd, shell=True)
        if err != 0:
            log.error(error_message) 
            sys.exit(1)


    def _get_remapping_data(self):
        """
        Fetches the git repo containing the remapping data and 
        pulls it into a temp directory.  If it already exists, we 
        just do a pull instead to make sure it is up-to-date.
        """
        root = "/tmp/resource_remapping/"
        if not os.path.exists(root):
            os.makedirs(root)

        repo_path = os.path.join(root, "redirector")

        if not os.path.exists(repo_path):
            self._run_or_exit("cd {dir}; git clone {repo}".format(dir=root,repo=GIT_REPO),
                "Failed to pull the remote repository at {0}".format(GIT_REPO))
        elif not self.options.nopull:
            log.debug("Pulling latest code")
            self._run_or_exit("cd {dir}; git pull origin master".format(dir=repo_path), 
                "Failed to pull the remote repository at {0}".format(GIT_REPO)) 
        else:
            log.debug("Code exists and nopull specified")

        return os.path.join(repo_path, "data/mappings")

