import csv
import json
import slugify

clashing_names = set(('electric-vehicle-charging-points',
                      'cycle-routes',
                      'hydrographic-data',
                      ))

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
            if dataset['name'] in clashing_names:
                dataset['name'] += '_'
            dataset['notes'] = row[0]  # For now...
            publisher = row[3].strip()
            if publisher == 'OAG':
                dataset['owner_org'] = 'oag'
            elif publisher == 'CAA':
                dataset['owner_org'] = 'civil-aviation-authority'
            elif publisher == 'Traveline':
                dataset['owner_org'] = 'traveline-information-limited'
            elif publisher == 'TfL / ATOC':
                dataset['owner_org'] = 'transport-for-london'
            elif publisher == 'OS':
                dataset['owner_org'] = 'ordnance-survey'
            elif publisher == 'ATOC':
                dataset['owner_org'] = 'atoc'
            elif publisher == 'Network Rail':
                dataset['owner_org'] = 'network-rail'
            elif publisher == 'DVLA':
                dataset['owner_org'] = 'driver-and-vehicle-licensing-agency'
            elif publisher == 'DVSA':
                dataset['owner_org'] = 'driver-vehicle-standards-agency'
            elif publisher == 'MCA':
                dataset['owner_org'] = 'maritime-and-coastguard-agency'
            elif publisher == 'CycleStreets':
                dataset['owner_org'] = 'cycle-streets'
            else:
                dataset['owner_org'] = 'department-for-transport'
            dataset['theme-primary'] = 'Transport'
            dataset['core-dataset'] = 'True'  # i.e. NII
            unpublished = row[2].strip() == 'Yes'
            if unpublished:
                dataset['unpublished'] = 'True'
                dataset['license_id'] = ''
            else:
                if row[6].strip() == 'OGL':
                    dataset['license_id'] = 'uk-ogl'
                else:
                    dataset['license_id'] = row[6].strip()

            if url:
                if not unpublished:
                    dataset['resources'] = [{'url': url, 'description': 'Website', 'format': 'HTML'}]
                else:
                    dataset['notes'] += '\n\n%s' % url

            if row[9].strip():
                dataset['notes'] += '\n\n%s' % row[9].strip()

            if row[3].strip() == 'operators':
                dataset['notes'] += "\n\nThis data is held by the transport operators"

            if row[3].strip() == 'Commercial':
                dataset['notes'] += "\n\nThis data is commercial data"

            jsonl.write("%s\n" % json.dumps(dataset))
