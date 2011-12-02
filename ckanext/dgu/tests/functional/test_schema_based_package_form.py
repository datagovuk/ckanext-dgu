"""
Tests the package form

The new package form is being refactored so as not to use sqlalchemy.  These
are the tests for this form.  For tests based on the sqlaclhemy-based form,
see 'test_package_gov3.py'.
"""

from ckan.tests import WsgiAppCase
from ckan.tests.html_check import HtmlCheckMethods

def url_for(**kwargs):
    """
    TODO: why isn't the real url_for picking up the correct route?
    """
    from ckan.tests import url_for as _url_for
    url = _url_for(**kwargs)
    return url.replace('dataset','package')

class TestFormRendering(WsgiAppCase, HtmlCheckMethods):
    """
    Tests that the various fields are represeted correctly in the form.
    """

    # input name -> (Label text , input type)
    _expected_fields = {
        'title':     ('Title *', 'input'),
        'name':      ('Identifier *', 'input'),

    }

    def test_new_form_has_all_fields(self):
        """
        Asserts that a form for a new package contains the various expected fields
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset)

        # quick check that we're checking the correct url
        assert "package" in offset

        for field, (label_text, input_type) in self._expected_fields.items():

            # e.g. <label for="title">Title *</label>
            self.check_named_element(response.body,
                                     'label',
                                     'for="%s"' % field,
                                     label_text)

            # e.g. <input name="title">
            self.check_named_element(response.body,
                                     input_type,
                                     'name="%s"' % field)


