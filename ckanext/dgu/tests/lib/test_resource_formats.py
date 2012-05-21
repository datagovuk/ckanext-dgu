from nose.tools import assert_equal

from ckanext.dgu.lib.resource_formats import ResourceFormats, match, get_all

class TestResourceFormats:
    def test_canonise(self):
        assert_equal(ResourceFormats.canonise('.XLS '), 'xls')
        
    def test_match(self):
        res_type_map = {
            # raw: expected_canonised
            'xls': 'XLS',
            '.xls': 'XLS',
            '.XLS': 'XLS',
            'csv': 'CSV',
            '.html': 'HTML',
            'html': 'HTML',
            'rdf/xml': 'RDF/XML',
            'rdf': 'RDF',
            '.rdf': 'RDF',
            '.RDF': 'RDF',
            'pdf': 'PDF',
            'PDF ': 'PDF',
            'ppt': 'PPT',
            'odp': 'ODP',
            'shp': 'SHP',
            'kml': 'KML',
            'doc': 'DOC',
            'json': 'JSON',
            }
        for raw, expected_match in res_type_map.items():
            assert_equal(match(raw), expected_match)
