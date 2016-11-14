'''GOV.UK link to data.gov.uk - command-line tool'''
# -*- coding: utf-8 -*-
import argparse
from pprint import pprint
import unicodecsv
import re
import os.path
from collections import defaultdict

from common import add_progress_bar
from running_stats import Stats

args = None

# get print to work with unicode chars
import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

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


DEFAULT_EXPORT_PUBLICATION_FILEPATH = 'publications.csv'


def export_publications():
    from ckanext.dgu.bin.common import load_config, add_progress_bar
    load_config(args.ckan_ini)
    from ckanext.dgu.model import govuk_publications as govuk_pubs_model
    from ckan import model

    headers = ['govuk_id', 'name', 'url', 'type', 'title', 'summary',
               'detail', 'published', 'last_updated', 'collections',
               'govuk_organizations']
    if args.include_attachments:
        headers += ['a_govuk_id', 'a_position', 'a_url', 'a_filename',
                    'a_format', 'a_title']
        if args.csv_filepath == DEFAULT_EXPORT_PUBLICATION_FILEPATH:
            args.csv_filepath = \
                args.csv_filepath.replace('.csv', '_and_attachments.csv')
        num_attachments = 0
        num_publications_without_attachments = 0

    out_rows = []
    publications = \
        model.Session.query(govuk_pubs_model.Publication)\
        .order_by(govuk_pubs_model.Publication.title)
    print 'Publications: %s' % publications.count()
    for pub in publications.yield_per(200):
        pub_row = {}
        pub_row['collections'] = ' '.join([c.name for c in pub.collections])
        pub_row['govuk_organizations'] = ' '.join(
            [o.name for o in pub.govuk_organizations])
        for key in headers:
            if key.startswith('a_') or key in pub_row:
                continue
            pub_row[key] = getattr(pub, key)
        pub_row['name'] = pub_row['name'].replace('publications/', '')
        if args.include_attachments:
            attachment_headers = [key.replace('a_', '') for key in headers
                                  if key.startswith('a_')]
            if pub.attachments:
                for attachment in pub.attachments:
                    attachment_row = pub_row.copy()
                    for key in attachment_headers:
                        attachment_row['a_' + key] = getattr(attachment, key)
                    out_rows.append(attachment_row)
                    num_attachments += 1
            else:
                attachment_row = pub_row.copy()
                for key in attachment_headers:
                    attachment_row['a_' + key] = ''
                out_rows.append(attachment_row)
                num_publications_without_attachments += 1
        else:
            out_rows.append(pub_row)
    if args.include_attachments:
        print 'Attachments: %s' % num_attachments
        print 'Publications without attachments: %s' % \
            num_publications_without_attachments

    out_filename = args.csv_filepath
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = unicodecsv.DictWriter(csv_write_file,
                                           fieldnames=headers,
                                           encoding='utf-8')
        csv_writer.writeheader()
        for row in out_rows:
            csv_writer.writerow(row)
    print 'Written', out_filename


def train_standard():
    if args.include_attachments:
        if args.csv_filepath == DEFAULT_EXPORT_PUBLICATION_FILEPATH:
            args.csv_filepath = \
                args.csv_filepath.replace('.csv', '_and_attachments.csv')

    in_filename = args.csv_filepath
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        publications = [row for row in csv_reader]
        headers = csv_reader.fieldnames
        print 'Publications: %s' % len(publications)

    standards = set()
    in_filename = 'standard_training.csv'
    if not os.path.exists(in_filename):
        training = {}
        training_headers = ['name', 'standard']
        print 'Creating new training set'
    else:
        with open(in_filename, 'rb') as csv_read_file:
            csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
            training = dict([
                (row['name'], row)
                for row in csv_reader])
            standards = set([
                row['standard'] for row in training.itervalues()])
            standards.remove('')
            training_headers = csv_reader.fieldnames
        print 'Training set: %s' % len(training)
    standards = list(standards)

    import random
    previous_pubs = []
    def get_random_pub():
        while True:
            pub = random.choice(publications)
            if pub['name'] in training:
                continue
            return pub

    pub = get_random_pub()
    while True:

        print '\n\n\n\n\n\nCategorize: %s\n' % pub['url']
        pub_str = '\n'.join((pub['name'].replace('-', ' '), pub['title'], pub['summary'], pub['detail'], pub['collections'].replace('-', ' '), pub.get('a_filename', ''), pub.get('a_title', '')))
        print pub_str.rstrip('\n ')
        print '\nStandards:'
        standards_numbered = dict(enumerate(sorted(standards)))
        for i, cat in standards_numbered.iteritems():
            print '  %s %s' % (i, cat)
        print 'n none'
        if previous_pubs:
            print 'b back'
        print 'q quit'
        valid_input = False
        while not valid_input:
            user_input = raw_input('> ')
            if (user_input in 'nqb' or
                    (is_number(user_input) and
                     int(user_input) < len(standards)) or
                    len(user_input) > 1):
                break
            print 'Invalid input'
        if user_input == 'q':
            break
        elif user_input == 'n':
            standard = ''
        elif user_input == 'b':
            pub = previous_pubs.pop()
            continue
        elif is_number(user_input) and int(user_input) < len(standards):
            standard = standards_numbered[int(user_input)]
        else:
            standard = user_input.strip()
            if standard not in standards:
                standards.append(standard)
        row = dict(
            name=pub['name'],
            standard=standard,
            )
        training[pub['name']] = row

        out_filename = 'standard_training.csv'
        with open(out_filename, 'wb') as csv_write_file:
            csv_writer = unicodecsv.DictWriter(csv_write_file,
                                               fieldnames=training_headers,
                                               encoding='utf-8')
            csv_writer.writeheader()
            for row in sorted(training.itervalues(),
                              key=lambda x: x['standard']):
                csv_writer.writerow(row)
        print 'Written', out_filename

        previous_pubs.append(pub)
        pub = get_random_pub()

def is_number(string):
    try:
        int(string)
        return True
    except ValueError:
        return False




def auto_standard():
    if args.include_attachments:
        if args.csv_filepath == DEFAULT_EXPORT_PUBLICATION_FILEPATH:
            args.csv_filepath = \
                args.csv_filepath.replace('.csv', '_and_attachments.csv')

    in_filename = args.csv_filepath
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        publications = [row for row in csv_reader]
        headers = csv_reader.fieldnames

    in_filename = 'standard_training.csv'
    if not os.path.exists(in_filename):
        training = {}
    else:
        with open(in_filename, 'rb') as csv_read_file:
            csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
            training = dict([
                (row['name'], row)
                for row in csv_reader])
    print 'Training set: %s' % len(training)

    spend_words = {
        'Cost of maintaining': -5,
        'spending with SMEs': -5,
        'household expenditure': -5,
        'International Aid Transparency Initiative': -5,
        'benchmarking tables': -5,
        'Local spending reports': -5,
        'oscar': -5,
        'Procurement spending data for DCLG': -5,
        'Revenue spending on free schools': -5,
        'Spending data for DCLG and government offices': -5,
        'Communities and Local Government group: Procurement expenditure': -5,
        'DCLG\'s arm\'s length bodies\' spending data': -5,
        'Contracts between the supplier': -5,
        'Merchant Category Code': -3,
        'hospitality': -3,
        'ministerial': -3,
        'gifts': -3,
        'major projects': -3,
        'spending controls': -3,
        'spending moratori(a|um)': -3,
        'moratori(a|um) exceptions': -3,
        'expenditure limit': -3,
        'quarterly data summary': -3,
        'public sector moratori(a|um)': -3,
        'government moratori(a|um)': -3,
        'inquiry': -3,
        'grants': -3,
        'review of ': -3,
        'Transaction explorer': -3,
        'budget': -3,
        'standing financial instructions': -3,
        'Government Procurement Card': -3,
        'gpc': -2,
        'ePCS': -2,
        'corporate credit card': -2,
        'procurement card': -1,
        'accounts': -1,
        'travel': -1,
        'spend(ing)?': 1,
        'expenditure': 1,
        'transactions': 1,
        'spend(ing)? over': 1,
        'spending data': 1,
        'departmental spend(ing)?': 1,
        'month by month expenditure': 1,
        'transaction number': 2,
        'financial transactions': 2,
        'transactions over': 2,
        '25,?000': 3,
        'spending with suppliers': 2,
        '25k': 2,
        'financial transactions': 3,
        'transaction spend data': 3,
        'spend transaction data': 3,
        #u'£25,?000': 3, doesn't match with leading £
        #u'£25k': 3, doesn't match with leading £
        'expenditure for the financial year': 3,
        'data on all payments': 3,
        'fire service expenditure': 5,
        u'(expenditure|spend|spending) (over|exceeding) £250': 5,
        u'(expenditure|spend|spending) (over|exceeding) £500': 5,
        u'(expenditure|spend|spending) (over|exceeding) £25k': 5,
        u'(expenditure|spend|spending) (over|exceeding) £25,?000': 5,
        u'spends exceeding £25,?000': 5,
        'dclg spending data': 5,
    }
    stats_detail = Stats()
    stats = Stats()
    stats_vs_training = Stats()
    stats_vs_training_detail = Stats()
    for pub in add_progress_bar(publications):
        if args.name and pub['name'] != args.name:
            continue
        pub_str = '. '.join((pub['name'].replace('-', ' '), pub['title'], pub['summary'], pub['detail'], pub['collections'].replace('-', ' '), pub.get('a_filename', ''), pub.get('a_title', '')))
        if args.name:
            print pub_str #.encode('latin7', 'ignore')
        score = 0
        for word, word_score in spend_words.iteritems():
            matches = re.findall(r'\b%s\b' % word, pub_str, re.I)
            weight = 1.0
            for match in matches:
                score += word_score * weight
                if weight == 1.0:
                    word_score_str = str(word_score)
                elif word_score > 0:
                    word_score_str += '+'
                else:
                    word_score_str += '-'
                weight /= 2.0  # words repeated have decreasing weight
            if matches and args.name:
                print '    score %s - %s' % (word_score_str, word)
        score = round(score, 1)
        if args.name:
            print '    Total score: %s' % score
        if score > 5:
            score = 5
        if score < 0:
            score = 0
        pub['is_spend_score'] = score
        stats_detail.add(u'Score %s' % int(score), pub['name'])
        if score >= 3:
            pub['is_spend'] = 'y'
            stats.add('Spend data', (score, pub['name']))
        else:
            pub['is_spend'] = ''
            stats.add('Not spend data', (score, pub['name']))

        if pub['name'] in training:
            training_is_spend = 'spend' in \
                training[pub['name']]['standard'].split()
            if training_is_spend == bool(pub['is_spend']):
                stats_vs_training.add('true', pub['name'])
                if pub['is_spend']:
                    stats_vs_training_detail.add('true positive', pub['name'])
                else:
                    stats_vs_training_detail.add('true negative', pub['name'])
            else:
                stats_vs_training.add('false', pub['name'])
                if pub['is_spend']:
                    stats_vs_training_detail.add('false positive', pub['name'])
                else:
                    stats_vs_training_detail.add('false negative', pub['name'])

    stats_detail.report_value_limit = 300
    if args.verbose:
        print '\nScores:\n', stats_detail
    print '\nOverall:\n', stats

    def percentage_and_fraction(num, denom):
        return '%.0f (%s/%s)' % (
            float(num/denom)*100,
            num, denom)
    def get_report_value(key):
        if key in stats_vs_training_detail:
            return stats_vs_training_detail.report_value(key)[0]
        return '0'

    if stats_vs_training:
        print '\nCheck vs training:'
        print '  Overall: %s' % percentage_and_fraction(
        len(stats_vs_training['true']), stats_vs_training_detail.get_total())
        print '  True positive: %s' % get_report_value('true positive')
        print '  False positive: %s' % get_report_value('false positive')
        print '  False negative: %s' % get_report_value('false negative')

    if 'is_spend' not in headers:
        headers.append('is_spend')
    if 'is_spend_score' not in headers:
        headers.append('is_spend_score')

    if not args.name:
        out_filename = args.csv_filepath
        with open(out_filename, 'wb') as csv_write_file:
            csv_writer = unicodecsv.DictWriter(csv_write_file,
                                               fieldnames=headers,
                                               encoding='utf-8')
            csv_writer.writeheader()
            for row in publications:
                csv_writer.writerow(row)
        print 'Written', out_filename
    else:
        print 'Not written - filter is applied'

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

    parser_export_publications = subparsers.add_parser('export-publications')
    parser_export_publications.add_argument('ckan_ini', help='CKAN config path')
    parser_export_publications.add_argument('--csv-filepath', default=DEFAULT_EXPORT_PUBLICATION_FILEPATH)
    parser_export_publications.add_argument('--include-attachments', action='store_true')
    parser_export_publications.set_defaults(func=export_publications)

    subparser = subparsers.add_parser('train-standard')
    subparser.add_argument('--csv-filepath', default=DEFAULT_EXPORT_PUBLICATION_FILEPATH)
    subparser.add_argument('--include-attachments', action='store_true')
    subparser.set_defaults(func=train_standard)

    subparser = subparsers.add_parser('auto-standard')
    subparser.add_argument('ckan_ini', help='CKAN config path')
    subparser.add_argument('--name', help='Filter to a particular name')
    subparser.add_argument('--csv-filepath', default=DEFAULT_EXPORT_PUBLICATION_FILEPATH)
    subparser.add_argument('-v', '--verbose', action='store_true')
    subparser.add_argument('--include-attachments', action='store_true')
    subparser.set_defaults(func=auto_standard)

    args = parser.parse_args()
    args.func()