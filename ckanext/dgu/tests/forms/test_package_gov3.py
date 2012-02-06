import re
import formalchemy

from nose.tools import assert_equal

import ckan.model as model
import ckan.forms
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import *
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.html_check import HtmlCheckMethods

from ckanext.dgu.forms.package_gov3 import get_gov3_fieldset
from ckanext.dgu.tests import *
from ckanext.dgu.testtools import test_publishers


def _get_blank_param_dict(pkg=None, fs=None):
    return ckan.forms.get_package_dict(pkg, blank=True, fs=fs)

def get_fieldset(**kwargs):
    if not kwargs.has_key('user_editable_groups'):
        kwargs['user_editable_groups'] = []
    if not kwargs.has_key('publishers'):
        kwargs['publishers'] = test_publishers
    return get_gov3_fieldset(**kwargs)


class TestFieldset(PylonsTestCase, WsgiAppCase, HtmlCheckMethods):
    @classmethod
    def setup_class(cls):
        PylonsTestCase.setup_class()
        cls.fixtures = Gov3Fixtures()
        cls.fixtures.create()

    @classmethod
    def teardown_class(cls):
        cls.fixtures.delete()

    def test_0_new_fields(self):
        fs = get_fieldset()
        fs = fs.bind(session=model.Session)
        out = fs.render()
        assert out
        assert 'Title' in out, out
        assert 'Identifier' in out, out
        assert 'Mandate' in out, out
        assert 'Revision' not in out, out
        assert 'Extras' not in out
        # default for license
        self.check_tag(out, 'option', 'value="uk-ogl"', 'selected="selected"')

    def test_0_edit_fields(self):
        fs = get_fieldset()
        pkg = model.Package.by_name(u'private-fostering-england-2009')
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        # check the right fields are rendered
        assert 'Title' in out, out
        assert 'Identifier' in out, out
        assert 'Mandate' in out, out
        assert 'Revision' not in out, out
        assert 'Extras' not in out

    def test_1_field_values(self):
        fs = get_fieldset()
        pkg = model.Package.by_name(u'private-fostering-england-2009')
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        expected_values = [
            (fs.title, 'Private Fostering'),
            (fs.date_released, '30/7/2009'),
            (fs.date_updated, '12:30 30/7/2009'),
            (fs.date_update_future, '1/7/2009'),
            (fs.update_frequency, 'annual'),
            (fs.geographic_granularity, 'regional'),
            (fs.geographic_coverage, None, 'England'),
            (fs.temporal_granularity, 'year'),
            (fs.temporal_coverage, None, '6/2008 - 6/2009'),
            (fs.national_statistic, 'checked', 'yes'),
            (fs.precision, 'Numbers to nearest 10, percentage to nearest whole number'),
            (fs.url, 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/index.shtml'),
            (fs.taxonomy_url, '', ''),
            (fs.published_by, 'Department for Education [3]', 'Department for Education'),
            (fs.published_via, '', ''),
            (fs.author, 'DCSF Data Services Group'),
            (fs.author_email, 'statistics@dcsf.gsi.gov.uk'),
            (fs.maintainer, '', ''),
            (fs.maintainer_email, '', ''),
            (fs.license_id, u'uk-ogl', u'OKD Compliant::UK Open Government Licence (OGL)'),
            ]
        for vals in expected_values:
            if len(vals) == 2:
                field, expected_render_str = vals
                expected_render_readonly_str = vals[1]
            else:
                field, expected_render_str, expected_render_readonly_str = vals
            if isinstance(field.renderer, (ckan.forms.common.SuggestedTextExtraField.SelectRenderer, formalchemy.fields.SelectFieldRenderer)):
                if expected_render_str.startswith('other='):
                    expected_render_str = 'other" type="text" value="' + expected_render_str.strip('other=')
                    expected_render_readonly_str = expected_render_readonly_str.strip('other=')
                elif not expected_render_str:
                    expected_render_str = 'selected="selected" value="">(None)'
                else:
                    # multiple choice must have the particular one selected
                    expected_render_str = 'selected" value="' + expected_render_str
            render = field.render()
            render_readonly = field.render_readonly()
            if expected_render_str == '':
                assert 'value=""' in render or 'value' not in render, \
                   'Expected a blank value in render of field %s but got \'%s\'' % \
                   (field.name, render)
            elif expected_render_str and expected_render_str.startswith('!'):
                assert expected_render_str[1:] not in render, \
                       'Expected \'%s\' NOT in render of field %s but got \'%s\'' % \
                       (expected_render_str, field.name, render)
            elif expected_render_str:
                assert expected_render_str in render, \
                       'Expected \'%s\' in render of field %s but got \'%s\'' % \
                       (expected_render_str, field.name, render)
            assert expected_render_readonly_str in render_readonly, \
                   'Expected \'%s\' in render_readonly of field %s but got \'%s\'' % \
                   (expected_render_readonly_str, field.name, render_readonly)
        self.check_tag(fs.geographic_coverage.render(), 'geographic_coverage-england', 'checked="checked"')
        self.check_tag(fs.geographic_coverage.render(), 'geographic_coverage-wales', '!checked="checked"')
        self.check_tag(fs.temporal_coverage.render(), 'temporal_coverage-from', 'value="12:30 24/6/2008"')
        self.check_tag(fs.temporal_coverage.render(), 'temporal_coverage-to', 'value="6/2009"')

    def test_2_field_publisher_none(self):
        # Create package
        CreateTestData.create_arbitrary({
            'name': u'test2',
            'title': u'Test2',
            'license': u'odc-pddl',
            'notes': u'some',
            })

        pkg = model.Package.by_name(u'test2')
        fs = get_fieldset()
        fs = fs.bind(pkg)
        out = fs.render()
        assert out

        for field, should_have_null_value in [(fs.published_by, False),
                                              (fs.published_via, True)]:
            pub_options = field.render()
            pub_options_readonly = field.render_readonly()
            assert '<select' in pub_options, pub_options
            assert_equal(('<option selected="selected" value="">(None)</option>' in pub_options), should_have_null_value, '%s %r' % (field, pub_options))
            if should_have_null_value:
                # published_by field is blank anyway because no value set.
                assert_equal('<p></p>', pub_options_readonly, '%s %r' % (field, pub_options_readonly))

        indict = ckan.forms.get_package_dict(pkg, fs=fs)
        fs = get_fieldset().bind(pkg, data=indict)
        assert not fs.validate()
        assert len(fs.errors) == 1, fs.errors
        assert fs.errors.has_key(fs.published_by), fs.errors.keys()
        
    def test_2_field_publisher_not_listed(self):
        # Create package
        CreateTestData.create_arbitrary({
            'name': u'test3',
            'title': u'Test3',
            'license': u'odc-pddl',
            'notes': u'some',
            'extras':{
                'published_by': u'Unheard-of Department [56]',
                'published_via': u'Another Unheard-of Department [57]',
                }
            })

        pkg = model.Package.by_name(u'test3')
        fs = get_fieldset()
        fs = fs.bind(pkg)
        out = fs.render()
        assert out

        for field, numbered_publisher, publisher in [
            (fs.published_by, u'Unheard-of Department [56]', u'Unheard-of Department *'),
            (fs.published_via, u'Another Unheard-of Department [57]', u'Another Unheard-of Department *')
            ]:
            pub_options = field.render()
            pub_options_readonly = field.render_readonly()
            assert '<select' in pub_options, pub_options
            expected_selected_field = '<option selected="selected" value="%s">%s</option>' % (numbered_publisher, publisher)
            assert expected_selected_field in pub_options, 'In field %s could not find %r:\n%r' % (field, expected_selected_field, pub_options)

        indict = ckan.forms.get_package_dict(pkg, fs=fs)
        fs = get_fieldset().bind(pkg, data=indict)
        assert fs.validate(), fs.errors


    def test_3_restrict(self):
        fs = get_fieldset(restrict=1)
        restricted_fields = ('national_statistic', )
        for field_name in restricted_fields:
            assert getattr(fs, field_name)._readonly, getattr(fs, field_name)
        
    def test_4_sync_new(self):
        newtagname = 'newtagname'
        indict = _get_blank_param_dict(fs=get_fieldset())
        prefix = 'Package--'
        indict[prefix + 'name'] = u'testname'
        indict[prefix + 'title'] = u'testtitle'
        indict[prefix + 'notes'] = u'some new notes'
        indict[prefix + 'tags'] = 'russian,tolstoy,%s' % newtagname
        indict[prefix + 'license_id'] = u'gpl-3.0'
        indict[prefix + 'date_released'] = u'27/11/2008'
        indict[prefix + 'date_updated'] = u'1/4/2008'
        indict[prefix + 'date_update_future'] = u'1/7/2010'
        indict[prefix + 'geographic_granularity'] = u'regional'
        indict[prefix + 'geographic_coverage-england'] = u'True'
        indict[prefix + 'geographic_coverage-wales'] = u'True'
        indict[prefix + 'temporal_granularity'] = u'year'
        indict[prefix + 'temporal_coverage-from'] = u'6/2008'
        indict[prefix + 'temporal_coverage-to'] = u'6/2009'
        indict[prefix + 'national_statistic'] = u'True'
        indict[prefix + 'precision'] = u'Nearest 1000'
        indict[prefix + 'taxonomy_url'] = u'http:/somewhere/about.html'
        indict[prefix + 'published_by'] = 'Ealing PCT [2]'
        indict[prefix + 'published_via'] = 'Department for Education [3]'
        indict[prefix + 'agency'] = u'Quango 1'
        indict[prefix + 'resources-0-url'] = u'http:/1'
        indict[prefix + 'resources-0-format'] = u'xml'
        indict[prefix + 'resources-0-description'] = u'test desc'
        fs = get_fieldset().bind(model.Package, data=indict, session=model.Session)
        CreateTestData.flag_for_deletion(pkg_names=[u'testname'],
                                         tag_names=[u'russian',
                                                    u'tolstoy'],)
        
        model.repo.new_revision()
        assert fs.validate()
        fs.sync()
        model.repo.commit_and_remove()

        outpkg = model.Package.by_name(u'testname')
        assert outpkg.title == indict[prefix + 'title']
        assert outpkg.notes == indict[prefix + 'notes']

        # test tags
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist, taglist
        assert u'tolstoy' in taglist, taglist
        assert newtagname in taglist

        # test licenses
        assert outpkg.license_id, outpkg
        assert outpkg.license, outpkg
        assert_equal(indict[prefix + 'license_id'], outpkg.license.id)

        # test resources
        assert len(outpkg.resources) == 1, outpkg.resources
        res = outpkg.resources[0]
        assert res.url == u'http:/1', res.url
        assert res.description == u'test desc', res.description
        assert res.format == u'xml', res.format

        # test gov fields
        extra_keys = outpkg.extras.keys()
        reqd_extras = {
            'date_released':'2008-11-27',
            'date_updated':'2008-04-01',
            'date_update_future':u'2010-07-01',
            'geographic_granularity':indict[prefix + 'geographic_granularity'],
            'geographic_coverage':'1010000: England, Wales',
            'temporal_granularity':indict[prefix + 'temporal_granularity'],
            'temporal_coverage-from':'2008-06',
            'temporal_coverage-to':'2009-06',
            'national_statistic':'yes',
            'precision':indict[prefix + 'precision'],
            'taxonomy_url':indict[prefix + 'taxonomy_url'],
            'published_by':indict[prefix + 'published_by'],
            'published_via':indict[prefix + 'published_via'],
            }
        for reqd_extra_key, reqd_extra_value in reqd_extras.items():
            assert reqd_extra_key in extra_keys, 'Key "%s" not found in extras %r' % (reqd_extra_key, extra_keys)
            assert outpkg.extras[reqd_extra_key] == reqd_extra_value, \
                 'Extra \'%s\' should equal \'%s\' but equals \'%s\'' % \
                 (reqd_extra_key, reqd_extra_value,
                  outpkg.extras[reqd_extra_key])

    def test_5_sync_update(self):
        # create initial package
        init_data = [{
            'name':'test_sync',
            'title':'test_title',
            'extras':{
              'external_reference':'ref123',
              'date_released':'2008-11-28',
              'date_updated':'2008-04-01',
              'date_update_future':'1/7/2009',
              'geographic_granularity':'testgran',
              'geographic_coverage':'1110000: England, Scotland, Wales',
              'temporal_granularity':'testtempgran',
              'temporal_coverage-from':'2007-01-08',
              'temporal_coverage-to':'2007-01-09',
              'national_statistic':'yes',
              'precision':'testprec',
              'taxonomy_url':'testtaxurl',
              'published_by':'Ealing PCT [2]',
              'published_via':'Department for Education [3]',
              },
            }]
        CreateTestData.create_arbitrary(init_data)
        pkg = model.Package.by_name(u'test_sync')
        assert pkg

        # edit it with form parameters
        indict = _get_blank_param_dict(pkg=pkg, fs=get_fieldset())
        prefix = 'Package-%s-' % pkg.id
        indict[prefix + 'name'] = u'testname2'
        indict[prefix + 'notes'] = u'some new notes'
        indict[prefix + 'tags'] = u'russian, tolstoy',
        indict[prefix + 'license_id'] = u'gpl-3.0'
        indict[prefix + 'date_released'] = u'27/11/2008'
        indict[prefix + 'date_updated'] = u'1/4/2008'
        indict[prefix + 'date_update_future'] = u'1/8/2010'
        indict[prefix + 'geographic_granularity'] = u'regional'
        indict[prefix + 'geographic_coverage-england'] = u'True'
        indict[prefix + 'geographic_coverage-wales'] = u'True'
        indict[prefix + 'temporal_granularity'] = u'year'
        indict[prefix + 'temporal_coverage-from'] = u'6/2008'
        indict[prefix + 'temporal_coverage-to'] = u'6/2009'
        indict[prefix + 'national_statistic'] = u'True'
        indict[prefix + 'precision'] = u'Nearest 1000'
        indict[prefix + 'taxonomy_url'] = u'http:/somewhere/about.html'
        indict[prefix + 'published_by'] = u'Department of Energy and Climate Change [4]'
        indict[prefix + 'published_via'] = u'National Health Service [1]'
        indict[prefix + 'resources-0-url'] = u'http:/1'
        indict[prefix + 'resources-0-format'] = u'xml'
        indict[prefix + 'resources-0-description'] = u'test desc'
        fs = get_fieldset().bind(pkg, data=indict)
        CreateTestData.flag_for_deletion(u'testname2')
        
        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        outpkg = model.Package.by_name(u'testname2')
        assert outpkg.notes == indict[prefix + 'notes']

        # test tags
        taglist = [ tag.name for tag in outpkg.tags ]
        assert u'russian' in taglist, taglist
        assert u'tolstoy' in taglist, taglist

        # test licenses
        assert outpkg.license
        assert indict[prefix + 'license_id'] == outpkg.license.id, outpkg.license.id

        # test resources
        assert len(outpkg.resources) == 1, outpkg.resources
        res = outpkg.resources[0]
        assert res.url == u'http:/1', res.url
        assert res.description == u'test desc', res.description
        assert res.format == u'xml', res.format

        # test gov fields
        extra_keys = outpkg.extras.keys()
        reqd_extras = {
            'date_released':'2008-11-27',
            'date_updated':'2008-04-01',
            'date_update_future':'2010-08-01',
            'geographic_granularity':indict[prefix + 'geographic_granularity'],
            'geographic_coverage':'1010000: England, Wales',
            'temporal_granularity':indict[prefix + 'temporal_granularity'],
            'temporal_coverage-from':'2008-06',
            'temporal_coverage-to':'2009-06',
            'national_statistic':'yes',
            'precision':indict[prefix + 'precision'],
            'taxonomy_url':indict[prefix + 'taxonomy_url'],
            'published_by':indict[prefix + 'published_by'],
            'published_via':indict[prefix + 'published_via'],            
            }
        for reqd_extra_key, reqd_extra_value in reqd_extras.items():
            assert reqd_extra_key in extra_keys, 'Key "%s" not found in extras %r' % (reqd_extra_key, extra_keys)
            assert outpkg.extras[reqd_extra_key] == reqd_extra_value, \
                 'Extra %s should equal %s but equals %s' % \
                 (reqd_extra_key, reqd_extra_value,
                  outpkg.extras[reqd_extra_key])

    def test_6_sync_update_restrict(self):
        # create initial package
        pkg_name = u'test_sync_restrict'
        init_data = [{
            'name':pkg_name,
            'title':'test_title',
            'extras':{
              'notes':'Original notes',
              'national_statistic':'yes',
              },
            }]
        CreateTestData.create_arbitrary(init_data)
        pkg = model.Package.by_name(pkg_name)
        assert pkg

        # edit it with form parameters
        indict = _get_blank_param_dict(pkg=pkg, fs=get_fieldset(restrict=1))
        prefix = 'Package-%s-' % pkg.id
        indict[prefix + 'notes'] = u'some new notes'
        # try changing restricted params anyway
        new_name = u'testname3' 
        indict[prefix + 'name'] = new_name
        indict[prefix + 'national_statistic'] = u'no'
        # don't supply national_statistic param at all
        fs = get_fieldset(restrict=1).bind(pkg, data=indict)
        CreateTestData.flag_for_deletion(new_name)
        
        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        assert not model.Package.by_name(pkg_name)
        outpkg = model.Package.by_name(new_name)
        assert outpkg
        # test sync worked
        assert outpkg.notes == indict[prefix + 'notes']

        # test gov fields
        extra_keys = outpkg.extras.keys()
        reqd_extras = {
            'national_statistic':'yes', # unchanged
            }
        for reqd_extra_key, reqd_extra_value in reqd_extras.items():
            assert reqd_extra_key in extra_keys, 'Key "%s" not found in extras %r' % (reqd_extra_key, extra_keys)
            assert outpkg.extras[reqd_extra_key] == reqd_extra_value, \
                 'Extra %s should equal %s but equals %s' % \
                 (reqd_extra_key, reqd_extra_value,
                  outpkg.extras[reqd_extra_key])

    def test_7_validate(self):
        # bad dates must be picked up in validation
        indict = _get_blank_param_dict(fs=get_fieldset())
        prefix = 'Package--'
        pkg_name = u'test_name7'
        indict[prefix + 'name'] = pkg_name
        indict[prefix + 'title'] = u'Test'
        indict[prefix + 'published_by'] = u'National Health Service [1]'
        indict[prefix + 'notes'] = u'abcd'
        indict[prefix + 'license_id'] = u'abcde'
        indict[prefix + 'date_released'] = u'27/11/2008'
        fs = get_fieldset().bind(model.Package, data=indict, session=model.Session)

        # initially validates ok
        assert fs.validate(), fs.errors

        # now add all problems
        bad_validating_data = [
            ('date_released', u'27/11/0208', 'out of range'),
            ('published_by', u'', 'Please enter a value'),
            ('published_via', u'Unheard of publisher', 'not one of the options'),
            ('national_statistic', u'yes',
             "'National Statistic' should only be checked if the package is "
             "'published by' or 'published via' the Office for National "
             "Statistics."),
            ]
        for field_name, bad_data, error_txt in bad_validating_data:
            indict[prefix + field_name] = bad_data
        fs = get_fieldset().bind(model.Package, data=indict, session=model.Session)
        # validation fails
        assert not fs.validate()
        for field_name, bad_data, error_txt in bad_validating_data:
            field = getattr(fs, field_name)
            err = fs.errors[field]
            assert error_txt in str(err), '%r should be in error %r' % (error_txt, err)

        # make sure it syncs without exception (this is req'd for a preview)
        CreateTestData.flag_for_deletion(pkg_name)
        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        # now fix publisher for national_statistics validation to pass
        indict[prefix + 'published_via'] = 'Office for National Statistics [345]'
        fs = get_fieldset().bind(model.Package, data=indict)
        fs.validate()
        error_field_names = [field.name for field in fs.errors.keys()]
        assert 'national_statistic' not in error_field_names, fs.errors

    def test_8_geo_coverage(self):
        # create initial package
        pkg_name = u'test_coverage'
        init_data = [{
            'name':pkg_name,
            'title':'test_title',
            'extras':{
              'geographic_coverage':'0010000: England, Scotland, Wales',
              },
            }]
        CreateTestData.create_arbitrary(init_data)
        pkg = model.Package.by_name(pkg_name)
        assert pkg

        # edit it with form parameters
        fs = get_fieldset()
        indict = ckan.forms.get_package_dict(pkg, fs=fs)
        prefix = 'Package-%s-' % pkg.id
        indict[prefix + 'geographic_coverage-england'] = u'True'
        indict[prefix + 'geographic_coverage-wales'] = u'True'
        indict[prefix + 'geographic_coverage-scotland'] = u'True'
        indict[prefix + 'geographic_coverage-global'] = u'True'
        fs = fs.bind(pkg, data=indict)
        
        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        outpkg = model.Package.by_name(pkg_name)
        assert_equal(outpkg.extras['geographic_coverage'], '1110010: Global, Great Britain (England, Scotland, Wales)')

