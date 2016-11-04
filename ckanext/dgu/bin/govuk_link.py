'''GOV.UK link to data.gov.uk - command-line tool'''
import argparse
from pprint import pprint

args = None

def scrape():
    from ckanext.dgu.lib.govuk_scraper import GovukPublicationScraper \
        as Scraper
    Scraper.init()

    if args.target.startswith('http'):
        url = args.target
        r = Scraper.requests.get(url)
        page_type = Scraper.extract_url_object_type(url)
        if page_type == 'publications':
            pub_name = Scraper.extract_name_from_url(url)
            publication = \
                Scraper.scrape_publication_page(r.content, url, pub_name)
            pprint(publication)
            Scraper.print_stats()
        elif page_type == 'organisations':
            org_scraped = Scraper.scrape_organization_page(r.content, url)
            pprint(org_scraped)
            print '\nFields:\n', Scraper.field_stats
        elif page_type == 'collections':
            collection = Scraper.scrape_collection_page(r.content, url)
            pprint(collection)
            print '\nCollections:\n', Scraper.collection_stats
        else:
            raise NotImplementedError(page_type)
    else:
        raise NotImplementedError(args.target)

def scrape_and_save():
    from ckanext.dgu.lib.govuk_scraper import GovukPublicationScraper \
        as Scraper
    from ckanext.dgu.bin.common import load_config
    Scraper.init()
    load_config(args.ckan_ini)

    if args.url:
        assert not (args.page or args.start_page or args.search_filter
                    or args.limit), 'Option not allowed when specifying a '\
            'particular url to scrape'
        url = args.url
        page_type = Scraper.extract_url_object_type(url)
        if page_type == 'publications':
            Scraper.scrape_and_save_publication(url)
            Scraper.print_stats()
        elif page_type == 'organisations':
            Scraper.scrape_and_save_organization(url)
            print '\nFields:\n', Scraper.field_stats
        elif page_type == 'collections':
            collection = Scraper.scrape_and_save_collection(
                url, including_publications=True)
            print collection
            print '\nCollections:\n', Scraper.collection_stats
            print '\nPublications:\n', Scraper.publication_stats
        else:
            raise NotImplementedError(page_type)
    else:
        options = dict(
            page=args.page,
            start_page=args.start_page,
            search_filter=args.search_filter,
            publication_limit=args.limit)
        Scraper.scrape_and_save_publications(**options)
        Scraper.print_stats()


def represents_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers()

    # subparsers
    parser_scrape = subparsers.add_parser('scrape')
    parser_scrape.add_argument('target', help='gov.uk URL or "1" page of search results or "all"')
    parser_scrape.set_defaults(func=scrape)

    parser_scrape_and_save = subparsers.add_parser('scrape-and-save', help='Scrape and save the result in the database plus any dependent attachments, organisations and collections')
    parser_scrape_and_save.add_argument('ckan_ini', help='CKAN config path')
    parser_scrape_and_save.add_argument('--url', help='gov.uk URL')
    parser_scrape_and_save.add_argument('--page', help='Only scrape the given page number of the publication search results')
    parser_scrape_and_save.add_argument('--start-page', default=1, help='Start scrape from the given page number of the publication search results')
    parser_scrape_and_save.add_argument('--search-filter', help='Filter publications')
    parser_scrape_and_save.add_argument('--limit', help='Stop after scraping this number of publications')
    parser_scrape_and_save.set_defaults(func=scrape_and_save)

    args = parser.parse_args()
    args.func()