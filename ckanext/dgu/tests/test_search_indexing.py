from nose.tools import assert_equal

from ckanext.dgu.search_indexing import SearchIndexing

resource_format_cleanup = SearchIndexing.resource_format_cleanup

class TestResourceFormatCleanup:
    def assert_format_clean(self, format, expected_cleaned_up_format):
        pkg = {'res_format': [format]}
        resource_format_cleanup(pkg)
        cleaned_up_format = pkg['res_format'][0]
        assert_equal(cleaned_up_format, expected_cleaned_up_format)
    
    def test_csv(self):
        self.assert_format_clean('csv', 'CSV')
        self.assert_format_clean('csv ', 'CSV')
        self.assert_format_clean('.csv', 'CSV')
        self.assert_format_clean('.Csv', 'CSV')
    def test_xls(self): self.assert_format_clean('xls', 'XLS')
    def test_xls(self): self.assert_format_clean('xlsx', 'XLS')
    def test_excel(self): self.assert_format_clean('excel', 'XLS')
    # CSV CSV/Zip XLS ODS RDF RDF/XML HTML+RDFa PPT ODP SHP KML TXT DOC JSON iCal SQL SQL/Zip PDF HTML
    def test_csv_zip(self): self.assert_format_clean('csv/zip', 'CSV / Zip')
    def test_ods(self): self.assert_format_clean('ods', 'ODS')
    #def test_rdf(self): self.assert_format_clean('rdf', 'RDF')
    def test_rdf_xml(self): self.assert_format_clean('rdf/xml', 'RDF')
    def test_html_rdfa(self): self.assert_format_clean('html+rdfa', 'RDFa')
    def test_zip(self): self.assert_format_clean('zip', 'Zip')
    def test_netcdf(self): self.assert_format_clean('netcdf', 'NetCDF')
    #def test_ical(self): self.assert_format_clean('ical', 'iCal')
    def test_shapefile(self): self.assert_format_clean('shapefile', 'SHP')
    def test_sql(self): self.assert_format_clean('sql', 'Database')
