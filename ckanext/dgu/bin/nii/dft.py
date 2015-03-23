import csv
import json
import slugify

with open('dft.csv') as csv_file:
    with open('dft.jsonl', 'w') as jsonl:
        reader = csv.reader(csv_file)
        reader.next() # Ignore header row
        for row in reader:
            url = row[10].strip()
            if url.startswith('http://data.gov.uk'):
                continue
            dataset = {}
            dataset['title'] = row[0]
            dataset['name'] = slugify.slugify(row[0])
            dataset['notes'] = row[0] # For now...
            dataset['owner_org'] = 'department-for-transport'
            if row[2].strip() == 'Yes':
                dataset['extras'] = [{'key': 'unpublished', 'value': True}]
                dataset['license_id'] = 'unpublished'
            else:
                if row[6].strip() == 'OGL':
                    dataset['license_id'] = 'uk-ogl'
                else:
                    dataset['license_id'] = None

            if url:
                dataset['resources'] = [{'url': url, 'name': 'Website'}]
                if dataset['license_id'] == 'unpublished':
                    print "Adding resource to unpublished dataset", dataset['title']

            jsonl.write("%s\n" % json.dumps(dataset))
