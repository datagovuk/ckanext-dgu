import sys

import ckan.plugins as p


class GovukPublicationsCommand(p.toolkit.CkanCommand):
    '''
    Manage the mirror of gov.uk publications.

    The available commands are:

        initdb - Initialize the database tables for the gov.uk publication data

        dropdb - Delete the database tables containing the gov.uk publication data

        list - Lists the data

        scrape - Scrape gov.uk

    e.g.

      List all reports:
      $ paster govuk_publications scrape -c development.ini

    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = None

    def __init__(self, name):
        super(GovukPublicationsCommand, self).__init__(name)

        self.parser.add_option('-p', '--page', dest='page',
            default='all', help='Page number to scrape, from the publication list (first is 1)')

    def command(self):
        import logging

        self._load_config()
        self.log = logging.getLogger('ckan.lib.cli')

        if not self.args:
            self.log.error('No arguments supplied and they are required')
            sys.stderr.write(self.usage)
            return
        else:
            cmd = self.args[0]
            if cmd == 'initdb':
                self._initdb()
            elif cmd == 'list':
                self._list()
            elif cmd == 'scrape':
                from ckanext.dgu.lib.govuk_publications import GovukPublicationScraper
                page = None if self.options.page == 'all' else (int(self.options.page) or 1)
                GovukPublicationScraper.scrape_publications(page=page)

    def _initdb(self):
        from ckanext.dgu.model import govuk_publications as govuk_pubs_model
        govuk_pubs_model.init_tables()
        self.log.info('Gov.uk Publications tables are setup')

    def _list(self):
        from ckanext.report.report_registry import ReportRegistry
        registry = ReportRegistry.instance()
        for plugin, report_name, report_title in registry.get_names():
            report = registry.get_report(report_name)
            date = report.get_cached_date()
            print '%s: %s %s' % (plugin, report_name,
                  date.strftime('%d/%m/%Y %H:%M') if date else '(not cached)')

