import csv
import json
import slugify
import codecs
import collections

# TODO
# Create script to add schemas and codelists? Can generate lookup table?
# Complete both lookup dictionaries
# Fill out 3 IDs for 3 orgs
# Check for name clashes

HSCIC_ID = CHOICES_ID = CQC_ID = '421a4052-275a-4617-8d9d-d958417710fd'

SCHEMA_LOOKUP = collections.defaultdict(lambda: '4f47b582-0054-4940-9438-c43e0495c4cc')
CODELIST_LOOKUP = collections.defaultdict(lambda: '5640d2df-6d38-47a2-9980-0afa9902f628')

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

with codecs.open('health.csv', encoding='cp1252') as csv_file:
    with open('health.jsonl', 'w') as jsonl:
        reader = unicode_csv_reader(csv_file)
        reader.next() # Ignore header row
        for row in reader:
            dataset = {}
            dataset['title'] = row[0]
            dataset['name'] = slugify.slugify(row[0])
            dataset['notes'] = row[16].strip() or row[0]

            if row[3] == 'HSCIC':
                dataset['owner_org'] = HSCIC_ID
            elif row[3] == 'NHS Choices':
                dataset['owner_org'] = CHOICES_ID
            else:
                dataset['owner_org'] = CQC_ID

            if row[9].strip() == 'OGL':
                dataset['license_id'] = 'uk-ogl'
            else:
                dataset['license_id'] = None

            url = row[15].strip()
            if url:
                dataset['resources'] = [{'url': url, 'name': 'Data'}]

            extras = []

            schema = row[13].strip()
            if schema:
                schema_list = json.dumps([SCHEMA_LOOKUP[schema]])
                extras.append({'key': 'schema', 'value': schema_list})

            codelists = [row[5].strip(), row[6].strip(), row[7].strip(), row[8].strip()]
            if any(codelists):
                codelist_list = json.dumps([CODELIST_LOOKUP[codelist] for codelist in codelists if codelist])
                extras.append({'key': 'codelist', 'value': codelist_list})

            if extras:
                dataset['extras'] = extras

            try:
                jsonl.write("%s\n" % json.dumps(dataset))
            except UnicodeDecodeError:
                print "Encoding Error", dataset['title']
