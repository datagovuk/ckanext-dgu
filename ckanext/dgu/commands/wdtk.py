import os
import csv
import time
import datetime
import logging
import requests
from ckan.lib.cli import CkanCommand


log = logging.getLogger('ckanext')


WDTK_REQUEST_URL = 'http://www.whatdotheyknow.com/body/%s'
WDTK_AUTHORITIES_URL = 'http://www.whatdotheyknow.com/body/all-authorities.csv'

direct_matches = {
'wales_office_swyddfa_cymru': 'wales_office',
'ons': 'office_for_national_statistics'
}

class PublisherMatch(CkanCommand):
    """
    Attempts to match publisher details with the information found at WDTK

    Retrieves from http://www.whatdotheyknow.com/body/all-authorities.csv the
    CSV and attempts to match up the url name there (the slug) with the
    publisher name automatically, leaving those it could not match.

    A working directory will need to be specified and so the command should be
    run with

        paster wdtk_publisher_match <WORKING_DIR> -c ../ckan/development.ini

    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        self.working_directory = self.args[0]
        log.info("Working directory set to %s" % self.working_directory)

        start = time.time()
        self.authorities_file = self._get_authorities_csv()
        self.publishers = {}

        pubs = model.Session.query(model.Group)\
            .filter(model.Group.type == 'publisher')\
            .filter(model.Group.state == 'active')
        for publisher in pubs:
            self.publishers[publisher.name.replace('-', '_')] = publisher
        log.info("Found %d publishers to process in DB" %
            len(self.publishers))

        matched = set()
        schools = 0
        count, processed = 0, 0
        with open(self.authorities_file, 'rU') as f:
            reader = csv.reader(f)
            for row in reader:
                slug = row[2]
                if '_school' in slug or '_college' in slug:
                    schools = schools + 1
                    continue

                homepage = row[4]
                publisher = self.publishers.get(slug, None)

                if not publisher:
                    publisher = self.nhs_guess(row)

                if not publisher and slug in direct_matches:
                    publisher = self.publishers[direct_matches[slug]]

                if publisher:
                    # Save as a publisher extra
                    count = count + 1
                    modified = False
                    if not publisher.extras.get('website-url'):
                        publisher.extras['website-url'] = homepage
                        modified = True
                    if not publisher.extras.get('WDTK_URL'):
                        publisher.extras['WDTK_URL'] = WDTK_REQUEST_URL % slug
                        modified = True
                    if modified:
                        processed = processed + 1
                        model.Session.add(publisher)
                        model.Session.commit()
                    matched.add(publisher.name.replace('-','_'))
        end = time.time()
        took = str(datetime.timedelta(seconds=end-start))
        log.info('Found %d publishers in CSV, updated %d publishers in %s' % (count, processed,took,))
        # diff = set(self.publishers.keys()) - matched
        # print 'Publishers we did not match'
        # print '==========================='
        # for p in diff:
        #    print p


    def council_guess(self, row):
        slug = row[2]
        if not 'council' in slug:
            return None


    def nhs_guess(self, row):
        slug = row[2]
        if not slug.startswith('nhs_'):
            return None

        # Try a semi-consistent PCT lookup
        partial = "%s_primary_care_trust" % slug[4:]
        publisher = self.publishers.get(partial)
        if publisher:
            return publisher

        partial = "%s_pct" % slug[4:]
        publisher = self.publishers.get(partial)
        if publisher:
            return publisher


        name = row[0]
        if '(PCT)' in name:
            name = name[:name.index(' (PCT)')]
            slug = name.lower().replace(' ', '_')
            publisher = self.publishers.get(slug)
            if publisher:
                return publisher

            slug = slug.replace('primary_care_trust', 'pct')
            publisher = self.publishers.get(slug)
            if publisher:
                return publisher

        return None



    def _get_authorities_csv(self):
        """
        Fetches the all-authorities csv from WDTK if we don't already
        have it in the last 24 hours
        """
        fetch, diff = True, 0
        f = os.path.join(self.working_directory, 'all-authorities.csv')
        if os.path.exists(f):
            mtime = os.path.getmtime(f)
            diff = time.time() - mtime
            fetch = diff > 86400

        if fetch:
            log.info("Fetching the authorities file from WDTK")
            r = requests.get(WDTK_AUTHORITIES_URL)
            if r.status_code == 200:
                with open(f, 'w') as w:
                    w.write(r.content.encode('utf-8','ignore'))
            else:
                raise RuntimeError("Cannot find the authorities file at %s" %
                    (WDTK_AUTHORITIES_URL,))
        else:
            log.info("Using local copy of the file which is %s old" %
                     str(datetime.timedelta(seconds=diff)))
        return f
