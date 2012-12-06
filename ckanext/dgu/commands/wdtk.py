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

        count, processed = 0, 0
        with open(self.authorities_file, 'rU') as f:
            reader = csv.reader(f)
            for row in reader:
                slug = row[2]
                homepage = row[4]
                publisher = self.publishers.get(slug, None)
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
        end = time.time()
        took = str(datetime.timedelta(seconds=end-start))
        log.info('Checked %d publishers and updated %d publishers in %s' % (count, processed, took,))

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
                    w.write(r.content)
            else:
                raise RuntimeError("Cannot find the authorities file at %s" %
                    (WDTK_AUTHORITIES_URL,))
        else:
            log.info("Using local copy of the file which is %s old" %
                     str(datetime.timedelta(seconds=diff)))
        return f
