from nose.tools import assert_equal

from ckanext.dgu.lib.formats import Formats

class TestFormats:
    def test_by_display_name(self):
        assert_equal(Formats.by_display_name()['JSON']['extension'], 'json')

    def test_by_extension(self):
        assert_equal(Formats.by_extension()['json']['display_name'], 'JSON')
        assert_equal(Formats.by_extension()['xlsx']['display_name'], 'XLS')

    def test_by_mime_type(self):
        assert_equal(Formats.by_mime_type()['text/x-json']['display_name'], 'JSON')

    def test_reduce(self):
        assert_equal(Formats.reduce('.XLS '), 'xls')
        
    def test_match(self):
        res_type_map = {
            # raw: expected_canonised
            'xls': 'XLS',
            '.xls': 'XLS',
            '.XLS': 'XLS',
            'csv': 'CSV',
            '.html': 'HTML',
            'html': 'HTML',
            'rdf/xml': 'RDF',
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
            assert Formats.match(raw), raw
            assert_equal(Formats.match(raw)['display_name'], expected_match)
