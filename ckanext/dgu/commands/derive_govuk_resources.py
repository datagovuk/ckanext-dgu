# -*- coding: utf-8 -*-
import os
import sys
import csv
import json
import collections
import datetime
import logging
import requests
from sqlalchemy import not_
from ckan.lib.cli import CkanCommand
from ckanext.dgu.bin.running_stats import StatsCount

log = logging.getLogger("ckanext")

ACCEPTED_FORMATS = ['application/vnd.ms-excel',
    'text/csv',
    'application/rdf+xml',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']


class GovUkResourceChecker(CkanCommand):
    """
    Iterates through gov.uk resources to find duplicates and attached data.

    A lot of the gov.uk resources point to a HTML file, which itself contains the
    link to the data.  In a similar manner to ons_scraper we want to make those HTML
    resources 'documentation' resources and if possible point directly to the data
    file itself.
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(GovUkResourceChecker, self).__init__(name)
        self.parser.add_option("-p", "--pretend",
                  dest="pretend", action="store_true",
                  help="Pretends to update the database, but doesn't really.")
        self.parser.add_option("-s", "--single",
                  dest="single",
                  default="",
                  help="Specifies a single dataset to work with")

        self.local_resource_map = collections.defaultdict(list)
        self.remap_stats = StatsCount()

        self.translog = csv.writer(open("derived.log", "wb"))
        self.translog.writerow(["PackageName", "ResourceID", "URL", "Action"])

    def record_transaction(self, package, resource, action):
        """ Write a record to the log file """
        row = [package.name, resource.id, action]
        self.translog.writerow(row)


    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        self._build_resource_map()
        for dataset, resources in self.local_resource_map.iteritems():
            self.process(dataset, resources)

        log.info(self.remap_stats.report(order_by_title=True))

    def process(self, dataset, resources):
        # We want distinct URLs in the resources, and don't really want
        # duplicates.  We should ignore (and eventually delete) dupes
        # UNLESS they have a hub-id in which case we should definitely
        # NOT delete them.
        import ckan.model as model

        dupes = []
        seen = []

        for r in resources[:]:
            if r.url not in seen:
                seen.append(r.url)
            else:
                print "Found a duplicate"
                dupes.append(r)
                resources.remove(r)

        log.info("Dataset '{0}' has {1} duplicates, in {2} resources".
            format(dataset.name, len(dupes), len(dupes) + len(resources)))

        # Handle the valid resources
        for resource in resources:
            if resource.resource_type == "documentation":
                log.info(" - Ignoring documentation resource")
                self.remap_stats.increment('Ignored documentation resource')
                continue

            log.debug("- Fetching attachments for {0}".format(resource.id))
            data = self._get_attachment(resource)
            if not data:
                log.info(" - No attachment for {0}".format(resource.url))
                continue

            attachments = []
            for att in data.get('attachments',[]):
                content_type = att.get('content_type')
                if content_type in ACCEPTED_FORMATS:
                    self.remap_stats.increment('Attachments found')
                    log.info(" - Found {0}".format(att.get("url")))
                    attachments.append(att)
                    break
                else:
                    log.info(" - Skipping attachment as it's {0}".format(content_type))

            if not attachments:
                continue

            for attachment in attachments:
                fmt = "CSV"
                u = attachment.get('url', '').lower()
                if u.endswith('.xls') or u.endswith('xlsx'):
                    fmt = "XLS"
                    self.remap_stats.increment('XLS')
                elif attachment.get('url', '').lower().endswith('.rdf'):
                    fmt = "RDF"
                    self.remap_stats.increment('RDF')
                else:
                    self.remap_stats.increment('CSV')

                # Add the new resource, and then mark the old resource as documentation
                log.info(" - Adding a new resource to {0}".format(dataset.name))
                self.remap_stats.increment('Attachments added')
                self.record_transaction(dataset, resource, "Created new from resource info")
                if not self.options.pretend:
                    # This should be the same type as the original to make sure we correctly
                    # handle time-series resources.
                    dataset.add_resource(url="http://www.gov.uk" + attachment.get('url'),
                             format=fmt,
                             resource_type=resource.resource_type,
                             description=attachment.get('title',''))
                    model.Session.add(dataset)
                    model.Session.commit()

                resource.resource_type = "documentation"
                resource.format = "HTML"
                log.info(" - Changing old resource to documentation")
                self.remap_stats.increment('Resources moved to documentation')
                self.record_transaction(dataset, resource, "Moved to documentation")
                if not self.options.pretend:
                    model.Session.add(resource)
                    model.Session.commit()

        # Handle the dupes, ignore them if they have a hub-id, potentially delete
        # them if they don't.
        log.info("Processing {} duplicates".format(len(dupes)))
        for resource in dupes:
            if 'hub-id' in resource.extras:
                # Don't delete ONS imported dataset
                log.info("Resource {} is an ONS resource, not deleting".format(resource.id))
                self.remap_stats.increment('ONS resources *not* deleted')
                continue

            log.info(" - Deleting duplicate {0} -> {1}".format(resource.url, resource.id))
            resource.state = 'deleted'
            self.remap_stats.increment('Deleted resource')
            self.record_transaction(dataset, resource, "Deleted dupe")
            if not self.options.pretend:
                model.Session.add(resource)
                model.Session.commit()
                log.info(" -- deleted {}".format(resource.id))
        model.Session.flush()

    def _get_attachment(self, resource):
        json_url = "".join([resource.url, ".json"])
        r = requests.head(json_url)
        if not r.status_code == 200:
            log.info("No JSON file at {0}".format(json_url))
            return None

        r = requests.get(json_url)
        if not r.status_code == 200:
            log.error("Failed to retrieve {0} after successful HEAD request".format(json_url))
            return None

        return json.loads(r.content)


    def _build_resource_map(self):
        import ckan.model as model

        # Find all non .csv/.xls links for gov.uk
        resources = model.Session.query(model.Resource).\
            filter(model.Resource.url.like("%/www.gov.uk/%")).\
            filter(not_(model.Resource.url.ilike("%.csv"))).\
            filter(not_(model.Resource.url.ilike("%.xls"))).\
            filter(not_(model.Resource.url.ilike("%.xlsx"))).\
            filter(not_(model.Resource.url.ilike("%.pdf"))).\
            filter(not_(model.Resource.url.ilike("%.rdf"))).\
            filter(not_(model.Resource.url.ilike("%.json"))).\
            filter(not_(model.Resource.url.ilike("%.doc"))).\
            filter(not_(model.Resource.resource_type=='documentation')).\
            filter(not_(model.Resource.resource_type=='timeseries'))
            #filter(model.Resource.state=='active')

        log.info("Found %d resources for www.gov.uk links" % resources.count())
        for r in resources:
            pkg = r.resource_group.package

            # If we only want one, then skip the others
            if self.options.single and not pkg.name == self.options.single:
                continue

            if pkg.state == 'active':
                self.local_resource_map[pkg].append(r)



