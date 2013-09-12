import os
import csv
import time
import datetime
import logging
import requests
import re
from ckan.lib.cli import CkanCommand


WDTK_REQUEST_URL = 'http://www.whatdotheyknow.com/body/%s'
WDTK_AUTHORITIES_URL = 'http://www.whatdotheyknow.com/body/all-authorities.csv'

DRY_RUN = False

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

    A working directory will need to be specified for caching the CSV from
    WDTK.

    Usage:

        paster wdtk_publisher_match <WORKING_DIR> -c ../ckan/development.ini

    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()

        log = logging.getLogger('ckanext')

        import ckan.model as model
        from ckanext.dgu.bin.running_stats import StatsList
        from ckanext.dgu.lib.publisher_matcher import PublisherMatcher

        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        self.working_directory = self.args[0]
        log.info("Working directory set to %s" % self.working_directory)

        start = time.time()
        self.authorities_file = self._get_authorities_csv()

        # Read in the WDTK publishers and store in matcher
        wdtk_publishers = {} # slug: name
        matcher = PublisherMatcher()
        with open(self.authorities_file, 'rU') as f:
            reader = csv.reader(f)
            for row in reader:
                name, short_name, slug = row[0:3]
                matcher.add_external_publisher(slug, name, short_name)
                wdtk_publishers[slug] = name.replace('\x92', "'").decode('utf8')

        # Match up DGU publishers
        publishers = model.Session.query(model.Group) \
            .filter(model.Group.type == 'organization') \
            .filter(model.Group.state == 'active').all()
        log.info("Found %d publishers to process in DB" %
            len(publishers))
        match_stats = StatsList()
        for publisher in publishers:

            match = matcher.match_to_external_publisher(publisher.title)

            if not match:
                match = matcher.match_to_external_publisher(publisher.extras.get('abbreviation', ''))

            if not match:
                match = matcher.match_to_external_publisher(re.sub('[-_]+', ' ', publisher.name))

            if not match and publisher.name in direct_matches:
                match = direct_matches[publisher.name]
                log.info(match_stats.add('Direct match', publisher.name))
                continue

            # We don't want to write any details automatically if we have
            # any existing phone, email or web details for FOI.
            have_previous_details = any([publisher.extras.get('foi-phone'),
                                         publisher.extras.get('foi-email'),
                                         publisher.extras.get('foi-web')])

            if not match:
                if have_previous_details:
                    log.info(match_stats.add('No match but already have FOI details', publisher.name))
                else:
                    log.info(match_stats.add('No match and still needs FOI details', publisher.name))
                continue

            # Save the publisher
            log.info('%s matches WDTK %s', publisher.name, match)

            # Store the match. Used for publisher_sync and publicbodies/nomen work.
            if not DRY_RUN and publisher.get('wdtk-id') != match and \
               publisher.get('wdtk-title') != wdtk_publishers[match]:
                publisher.extras['wdtk-id'] = match
                publisher.extras['wdtk-title'] = wdtk_publishers[match]
                model.Session.commit()

            # Check if previous WDTK details are still correct
            wdtk_url = WDTK_REQUEST_URL % match
            if 'whatdotheyknow' in publisher.extras.get('foi-web', ''):
                if publisher.extras['foi-web'] == wdtk_url:
                    log.info(match_stats.add('Match, but already have WDTK FOI details', publisher.name))
                    continue
                else:
                    log.info(match_stats.add('Match, and correcting WDTK FOI details', publisher.name))
            elif have_previous_details:
                log.info(match_stats.add('Match, but already have FOI details', publisher.name))
                continue
            else:
                log.info(match_stats.add('Match and added FOI details', publisher.name))

            if not DRY_RUN:
                publisher.extras['foi-web'] = wdtk_url
                model.Session.commit()

        print 'Full list of publishers not matched:'
        for name in match_stats['No match and still needs FOI details'] + match_stats['No match but already have FOI details']:
            print name, repr(model.Group.by_name(name).title)

        end = time.time()
        took = str(datetime.timedelta(seconds=end-start))
        log.info('Time taken: %s' % took)
        print match_stats.report()

        if DRY_RUN:
            print 'NB: No changes made - this was a dry run'

    def _get_authorities_csv(self):
        """
        Fetches the all-authorities csv from WDTK if we don't already
        have it in the last 24 hours
        """
        log = logging.getLogger('ckanext')
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

