import mock
from nose.tools import assert_equal
from ckanext.dgu.bin.licence_tidy import LicenceTidy


class TestTidy(object):
    @mock.patch('ckanext.dgu.bin.licence_tidy.LicenceTidy.__init__')
    def _try_fields(self, in_fields, expected_out_fields,
                    mock_init):
        mock_init.return_value = None
        LicenceTidy.ckan = mock.MagicMock()
        LicenceTidy.ckan.action.license_list.return_value = [{'id': 'uk-ogl'}]
        dataset = {'name': 'test',
                   'license_id': in_fields.get('license_id', None),
                   'extras': []}
        for key in ('licence', 'licence_url', 'licence_url_title'):
            if key in in_fields:
                dataset['extras'].append({'key': key, 'value': in_fields[key]})

        tidied_dataset, updated = LicenceTidy('').get_tidied_dataset(dataset)

        out_fields = {'license_id': tidied_dataset['license_id']}
        for extra in tidied_dataset['extras']:
            if extra['key'] in ('licence', 'licence_url', 'licence_url_title'):
                out_fields[extra['key']] = extra['value']
        assert_equal(out_fields, expected_out_fields)

    def test_form_ogl(self):
        self._try_fields(
            {'license_id': 'uk-ogl'},
            {'license_id': 'uk-ogl'}
            )

    def test_form_free_text(self):
        self._try_fields(
            {'license_id': 'Supplied under section 47 and 50 of the Copyright, Designs and Patents Act 1988 and Schedule 1 of the Database Regulations (SI 1997/3032)'},
            {'license_id': '',
             'licence': 'Supplied under section 47 and 50 of the Copyright, Designs and Patents Act 1988 and Schedule 1 of the Database Regulations (SI 1997/3032)'}
            )

    def test_ckan_harvest_new_id(self):
        self._try_fields(
            {'license_id': 'uk-ogl3'},
            {'license_id': '',
             'licence': 'uk-ogl3'}
            )

    def test_none_string(self):
        self._try_fields(
            {'license_id': 'None',
             'licence': "['License available']"},
            {'license_id': '',
             'licence': "License available"},
            )

    def test_inspire_just_ogl(self):
        self._try_fields(
            {'license_id': None,
             'licence': '[\"Open Government Licence\"]'},
            {'license_id': 'uk-ogl'}
            )

    def test_inspire_ogl_as_part(self):
        self._try_fields(
            {'license_id': None,
             'licence': '[\"Open Government Licence\", \"Other terms\"]'},
            {'license_id': 'uk-ogl',
             'licence': 'Open Government Licence; Other terms'}
            )

    def test_inspire_nothing(self):
        self._try_fields(
            {'license_id': None,
             'licence': ''},
            {'license_id': ''}
            )

    def test_inspire_free_text(self):
        self._try_fields(
            {'license_id': None,
             'licence': "['License available']"},
            {'license_id': '',
             'licence': "License available"},
            )

    def test_inspire_multiple_text(self):
        self._try_fields(
            {'license_id': None,
             'licence': "['Copyright', 'Licence', 'IPR', 'Restricted']"},
            {'license_id': '',
             'licence': "Copyright; Licence; IPR; Restricted"},
            )

    def test_inspire_free_text_and_url(self):
        self._try_fields(
            {'license_id': None,
             'licence': "['License available', 'Good']",
             'licence_url': 'http://license.com/terms.html'},
            {'license_id': '',
             'licence': 'License available; Good; http://license.com/terms.html'},
            )

    def test_inspire_free_text_and_multiple_urls(self):
        self._try_fields(
            {'license_id': None,
             'licence': "['License available', 'Good', 'http://license.com/terms2.html']",
             'licence_url': 'http://license.com/terms1.html'},
            {'license_id': '',
             'licence': 'License available; Good; http://license.com/terms2.html; http://license.com/terms1.html'},
            )

    def test_inspire_anchor(self):
        self._try_fields(
            {'license_id': None,
             'licence': "['License available', 'Good', 'http://license.com/terms2.html']",
             'licence_url': 'http://license.com/terms1.html',
             'licence_url_title': 'The terms'},
            {'license_id': '',
             'licence': 'License available; Good; http://license.com/terms2.html; The terms - http://license.com/terms1.html'},
            )

    def test_inspire_just_anchor(self):
        self._try_fields(
            {'license_id': None,
             'licence': "",
             'licence_url': 'http://license.com/terms.html',
             'licence_url_title': 'The terms'},
            {'license_id': '',
             'licence': 'The terms - http://license.com/terms.html'},
            )
