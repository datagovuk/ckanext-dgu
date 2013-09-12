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

    def stripped(self, s):
        import string
        exclude = set(string.punctuation)
        stopped = ['and', 'of', 'it', 'the']
        s = s.lower()
        s = ''.join(c for c in s if not c in exclude)
        s = ' '.join(w for w in s.split() if not w in stopped)
        return s

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
        self.publishers_full = {}
        self.missing = {}

        pubs = model.Session.query(model.Group)\
            .filter(model.Group.type == 'organization')\
            .filter(model.Group.state == 'active')
        for publisher in pubs:
            self.publishers[publisher.name.replace('-', '_')] = publisher
            self.publishers_full[self.stripped(publisher.title)] = publisher
            self.missing[publisher] = 1

        log.info("Found %d publishers to process in DB" %
            len(self.publishers))

        matched = set()
        schools = 0
        count, processed = 0, 0
        with open(self.authorities_file, 'rU') as f:
            reader = csv.reader(f)
            for row in reader:
                name = row[0]
                slug = row[2]
                homepage = row[4]
                publisher = self.publishers.get(slug, None)

                if not publisher:
                    publisher = self.nhs_guess(row)

                if not publisher and slug in direct_matches:
                    publisher = self.publishers[direct_matches[slug]]

                # Match on the first field if we still don't have a publisher.
                if not publisher:
                    publisher = self.publishers_full.get(self.stripped(name))

                if not publisher:
                    publisher = self.council_guess(row)

                if publisher:
                    # Save as a publisher extra
                    count = count + 1
                    modified = False

                    # We don't want to write any details automatically if we have
                    # any existing phone, email or web details for FOI.
                    have_previous_details = any([publisher.extras.get('foi-phone'),
                                                publisher.extras.get('foi-email'),
                                                publisher.extras.get('foi-web')])

                    if not publisher.extras.get('website-url'):
                        publisher.extras['website-url'] = homepage
                        modified = True
                    if not have_previous_details:
                        publisher.extras['foi-web'] = WDTK_REQUEST_URL % slug
                        modified = True
                    else:
                        log.info("Skipping {pubname} as details already exist".format(pubname=publisher.name))
                    if modified:
                        processed = processed + 1
                        model.Session.add(publisher)
                        model.Session.commit()
                    matched.add(publisher.name.replace('-','_'))
                    del self.missing[publisher]

        output_file = open(os.path.join(self.working_directory, 'missing.txt'), 'w')
        for k in self.missing.keys():
            output_file.write('%s\n' % k.name)
        output_file.close()

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
        if slug.endswith('_borough_council'):
            slug = slug[:-len('_borough_council')]
        else:
            return None

        part = 'london_borough_of_%s' % slug
        publisher = self.publishers.get(part)
        if publisher:
            return publisher

        publisher = self.publishers.get("borough_of_%s" % slug)
        if publisher:
            return publisher

        publisher = self.publishers.get("royal_borough_of_%s" % slug)
        if publisher:
            return publisher

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
                    try:
                        w.write(r.content.encode('utf-8','ignore'))
                    except:
                        w.write(r.content)
            else:
                raise RuntimeError("Cannot find the authorities file at %s" %
                    (WDTK_AUTHORITIES_URL,))
        else:
            log.info("Using local copy of the file which is %s old" %
                     str(datetime.timedelta(seconds=diff)))
        return f
