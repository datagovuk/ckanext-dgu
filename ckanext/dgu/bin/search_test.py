import argparse
import traceback
from pprint import pprint
import json

from solr import SolrException

import common

args = None

# Sample real query
# {
# 'bf': 'core_dataset^20 register^100',
# 'facet': 'true',
# 'facet.field': ['groups',
#              'tags',
#              'res_format',
#              'license',
#              'resource-type',
#              'UKLP',
#              'license_id-is-ogl',
#              'publisher',
#              'openness_score',
#              'spatial-data-service-type',
#              'all_themes',
#              'theme-primary',
#              'unpublished',
#              'broken_links',
#              'schema_multi',
#              'codelist_multi',
#              'collection'],
# 'facet.limit': '50',
# 'facet.mincount': 1,
# 'fl': 'id validated_data_dict',
# 'fq': [u' capacity:"public" +site_id:"localhost" +state:active'],
# 'q': '*:*',
# 'qf': 'title^4 name^3 notes^2 text organization_titles^0.3 extras_harvest_document_content^0.2',
# 'rows': 11,
# 'sort': 'score desc, popularity desc, name asc',
# 'start': 0,
# 'wt': 'json'}

def scores():
    query = {
        'bf': 'core_dataset^20 register^100',
        'fl': 'name score',
        'fq': [u' capacity:"public" +site_id:"localhost" +state:active'],
        'q': args.q,
        'qf': 'title^4 name^3 notes^2 text organization_titles^0.3 extras_harvest_document_content^0.2',
        'rows': 11,
        'sort': 'score desc, popularity desc, name asc',
        'start': 0,
        'wt': 'json'}
    data = run_solr_query(query)
    pprint(data)
    for doc in data['response']['docs']:
        print '{:.2f} {}'.format(doc['score'], doc['name'])



# based on ckan.lib.search.common.make_connection
def make_connection():
    from solr import SolrConnection
    solr_url = common.get_config_value_without_loading_ckan_environment(
        args.ckan_ini, 'solr_url')
    assert solr_url is not None
    return SolrConnection(solr_url)

def run_solr_query(query):
    conn = make_connection()
    try:
        solr_response = conn.raw_query(**query)
    except SolrException, e:
        traceback.print_exc()
        import pdb; pdb.set_trace()
    data = json.loads(solr_response)

    # return datasets as names rather than dict(id=, validated_data_dict=)
    # names = [json.loads(doc['validated_data_dict'])['name']
    #          for doc in data['response']['docs']]
    # data['response']['docs'] = names

    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ckan_ini', help='Filepath of the ckan.ini')
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('scores')
    subparser.set_defaults(func=scores)
    subparser.add_argument('-q',
                           default='*:*',
                           help='Query string')

    args = parser.parse_args()

    # call the function
    args.func()
