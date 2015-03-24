"""
Convert schema file in CSV format into JSON Table Schema format

http://dataprotocols.org/json-table-schema/
"""
import csv
import json
import sys

def convert(input_file_name, output_file_name):
    fields = []
    with open(input_file_name) as input_file:
        reader = csv.reader(input_file)
        for i, row in enumerate(reader):
            if i == 0:
                continue

            row_object = {}
            row_object['name'] = row[1]
            if row_object['name'] == 'Null':
                continue

            try:
                row_object['required'] = row[3] == 'Yes'
            except IndexError:
                row_object['required'] = False


            try:
                row_object['maxLength'] = int(row[2])
                if row_object['maxLength'] == 0:
                    continue
            except (ValueError, IndexError):
                # Probably row[2] == ''
                pass

            fields.append(row_object)

    with open(output_file_name, 'w') as output_file:
        output_file.write(json.dumps({"fields": fields}, indent=4))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: convert_schema.py <schema.csv>"
        sys.exit(1)
    input_file_name = sys.argv[1]
    output_file_name = input_file_name.replace('.csv', '.json')
    
    convert(input_file_name, output_file_name)
