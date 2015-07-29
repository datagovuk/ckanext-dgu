'''
Takes the OpenSpending Report HTML and extracts the data.

(Would normally just go straight to the data, but the server is down.)
'''

from optparse import OptionParser
import os.path
import csv

import lxml.html

def spend_scrape(input_filepath, output_filepath, **options):
    doc_html = open(os.path.expanduser(input_filepath), 'rb').read()
    doc = lxml.html.fromstring(doc_html)
    with open(output_filepath, 'wb') as out_file:
        csv_writer = csv.writer(out_file)
        column_headings = None
        for category in doc.xpath('//h4'):
            table = category.xpath('following-sibling::table')[0]
            category_name = category.xpath('text()')[0].strip()

            column_headings_local = table.xpath('.//th/text()')
            column_headings_local = ['Publisher Category'] + column_headings_local
            column_headings_local = [ch.encode('utf8') for ch in column_headings_local]
            if column_headings is not None:
                assert column_headings == column_headings_local, (column_headings, column_headings_local)
            else:
                print column_headings
                column_headings = column_headings_local
                csv_writer.writerow(column_headings)

            for row in table.xpath('./tbody/tr'):
                try:
                    td_list = row.xpath('./td')
                    title_texts = td_list[0].xpath('./a/text()')
                    if len(title_texts) == 2:
                        title = title_texts[0]
                    else:
                        title = td_list[0].xpath('./text()')[0].strip(' \n()')
                    row_values = [category_name, title]
                    for td in td_list[1:]:
                        td_text = td.xpath('./text()')
                        row_values.append(td_text[0].strip() if td_text else None)
                    # add padding
                    row_values += [] * (len(column_headings) - len(row_values))
                    csv_writer.writerow(row_values)
                    print row_values
                except IndexError, e:
                    import pdb; pdb.set_trace()

if __name__ == '__main__':
    usage = __doc__ + '\n\nUsage: %prog [options] index.html output.csv'
    parser = OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    input_filepath, output_filepath = args
    spend_scrape(input_filepath, output_filepath, **vars(options))
