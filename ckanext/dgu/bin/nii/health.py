import csv
import json
import slugify
import codecs
import collections

# TODO
# Check for name clashes

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

codes = set()

with codecs.open('health.csv', encoding='cp1252') as csv_file:
    with open('health.jsonl', 'w') as jsonl:
        reader = unicode_csv_reader(csv_file)
        reader.next() # Ignore header row
        for row in reader:
            dataset = {}
            dataset['title'] = row[0]
            dataset['name'] = slugify.slugify(row[0])
            dataset['notes'] = (row[16].strip() or row[0]).replace('\n', '\n\n')
            dataset['theme-primary'] = 'Health'
            dataset['core-dataset'] = 'True'  # i.e. NII

            if row[3] == 'HSCIC':
                dataset['owner_org'] = 'health-and-social-care-information-centre'
            elif row[3] == 'NHS Choices':
                dataset['owner_org'] = 'nhs-choices'
            else:
                dataset['owner_org'] = 'care-quality-commission'

            if row[9].strip() == 'OGL':
                dataset['license_id'] = 'uk-ogl'
            else:
                dataset['license_id'] = None

            url = row[15].strip()
            if url:
                dataset['resources'] = [{'url': url, 'description': 'Data', 'format': 'CSV'}]

            schema = row[13].strip()
            if schema:
                dataset['schema'] = [schema]

            codelists = [row[5].strip(), row[6].strip(), row[7].strip(), row[8].strip()]
            if any(codelists):
                codes.update(codelists)
                dataset['codelist'] = [code for code in codelists if code]

            try:
                jsonl.write("%s\n" % json.dumps(dataset))
            except UnicodeDecodeError:
                print "Encoding Error", dataset['title']

if False:  # don't need to produce the codelists repeatedly with differing ids
    import uuid
    with open('codelists.jsonl', 'w') as codelists:
        for code in codes:
            if not code:
                continue
            id = str(uuid.uuid4())
            codelists.write("%s\n" % json.dumps({'id': id, 'title': code, 'url': ''}))
