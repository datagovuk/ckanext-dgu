import os
import csv
import logging
from ckan.lib.cli import CkanCommand

log = logging.getLogger('ckanext')

old_licenses = ['ukcrown-withrights',
                'UK Crown Copyright with data.gov.uk rights',
                'UK Crown Copyright with data.gov.uk rights',
                'UK Crown Copyright with data.gov.uk rights']

class UpdateLicense(CkanCommand):
    """
    Updates old license ids with their new equivalents

    license_id "ukcrown-withrights" -> "uk-ogl"
    e.g. http://data.gov.uk/dataset/financial-transactions-data-calderstones-partnership-nhs-foundation-trust-january-12

    license_id "UK Crown Copyright with data.gov.uk rights" -> "uk-ogl"
    e.g. http://data.gov.uk/dataset/june-to-july-2012-spend-over-25-000-in-kingston-hospital

    license_id "UK Crown Copyright with data.gov.uk rights" -> "uk-ogl"
    e.g. http://data.gov.uk/dataset/april-2012-spend-over-25-000-in-kingston-hospital

    license_id "UK Crown Copyright with data.gov.uk rights" -> "uk-ogl"
    e.g. http://data.gov.uk/dataset/march-2012-financial-transactions-data-kingston-hospital-nhs-trust
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        count = 0
        for pkg in model.Session.query(model.Package).all():
            if pkg.license_id in old_licenses:
                pkg.license_id = 'uk-ogl'
                count = count + 1
                model.Session.add(pkg)
        if count:
            model.Session.commit()
        log.info("Converted %d licenses" % count)

