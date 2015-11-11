import sys

import ckan.plugins as p


class GovukPublicationsCommand(p.toolkit.CkanCommand):
    '''
    Manage the mirror of gov.uk publications.

    The available commands are:

        initdb - Initialize the database tables for the gov.uk publication data

        dropdb - Delete the database tables containing the gov.uk publication data

        scrape - Scrape gov.uk

        autolink - Find clear links between gov.uk and DGU

        fixup - Finds local resource pointing to publications and tries to link
                   them to attachments

        autoadd - Add new dataset or update existing dataset based on links

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

        self.parser.add_option('--page', dest='page',
            default='all', help='Page number to scrape, from the publication list (first is 1)')
        self.parser.add_option('--start-page', dest='start_page',
            default='1', help='Page number to start scraping from, of the publication list (first is 1)')
        self.parser.add_option('--publication', dest='publication',
            help='Publication URL to scrape')
        self.parser.add_option('--organization', dest='organization',
            help='Organization name or URL to scrape')
        self.parser.add_option('-r', '--resource', dest='resource',
            help='Resource ID to autolink')
        self.parser.add_option('-d', '--dataset', dest='dataset',
            help='Dataset name to autolink')

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
                from ckanext.dgu.lib.govuk_scraper import GovukPublicationScraper
                GovukPublicationScraper.init()
                if self.options.page != 'all':
                    page = int(self.options.page)
                    GovukPublicationScraper.scrape_and_save_publications(page=page,
                        search_filter='publication_filter_option=transparency-data')
                elif self.options.start_page != '1':
                    start_page = int(self.options.start_page)
                    GovukPublicationScraper.scrape_and_save_publications(start_page=start_page)
                elif self.options.publication:
                    if 'http' not in self.options.publication:
                        sys.stderr.write('Publication needs to be a URL')
                        return
                    GovukPublicationScraper.scrape_and_save_publication(self.options.publication)
                    GovukPublicationScraper.print_stats()
                elif self.options.organization:
                    if 'http' not in self.options.organization:
                        self.options.organization = 'https://www.gov.uk/government/organisations/' + self.options.organization
                    GovukPublicationScraper.scrape_and_save_organization(self.options.organization)
                    print '\nFields:\n', GovukPublicationScraper.field_stats
                else:
                    GovukPublicationScraper.scrape_and_save_publications(search_filter='publication_filter_option=transparency-data')
            elif cmd == 'autolink':
                from ckanext.dgu.lib.govuk_links import GovukPublicationLinks
                GovukPublicationLinks.autolink(resource_id=self.options.resource,
                                               dataset_name=self.options.dataset)
            elif cmd == "fixup":
                from ckanext.dgu.lib.govuk_links import GovukPublicationLinks
                GovukPublicationLinks.fix_local_resources(resource_id=self.options.resource,
                                               dataset_name=self.options.dataset)
            elif cmd == 'autoadd':
                from ckanext.dgu.lib.govuk_add import GovukPublications
                GovukPublications.autoadd(publication_url=self.options.publication)



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
