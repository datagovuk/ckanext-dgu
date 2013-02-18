from nose.tools import assert_equal

from ckanext.dgu.lib.formats import Formats
import os

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

    def test_fugue_icons_exist(self):
        # List all icon files in the fugue folder
        path = os.path.dirname(__file__)   # /ckanext/dgu/tests/lib
        path = os.path.dirname(path)       # /ckanext/dgu/tests
        path = os.path.dirname(path)       # /ckanext/dgu
        # /ckanext/dgu/theme/public/images/fugue
        path = os.path.join(path, 'theme', 'public', 'images', 'fugue') 
        assert os.path.isdir(path)
        files = os.listdir(path)
        # Each format should have an icon in that folder
        assert 'document.png' in files, 'document.png not found in %s' % path
        for fmt in Formats.by_display_name().values():
            if fmt['icon']=='': continue
            icon_name = fmt['icon']+'.png'
            assert icon_name in files, '%s not found in %s' % (icon_name,path)

