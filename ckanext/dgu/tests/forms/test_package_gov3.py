from nose.tools import assert_equal

import ckan.model as model
import ckan.forms
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import *
from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests.html_check import HtmlCheckMethods

from ckanext.dgu.forms.package_gov3 import get_gov3_fieldset
from ckanext.dgu.tests import *

#from pylons import config

def _get_blank_param_dict(pkg=None, fs=None):
    return ckan.forms.get_package_dict(pkg, blank=True, fs=fs)

def get_fieldset(**kwargs):
    if not kwargs.has_key('user_editable_groups'):
        kwargs['user_editable_groups'] = []
    return get_gov3_fieldset(**kwargs)


class TestFieldset(PylonsTestCase, HtmlCheckMethods):
    @classmethod
    def setup_class(self):
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()

    @classmethod
    def teardown_class(self):
        self.fixtures.delete()

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
        print out
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
            (fs.national_statistic, 'True', 'yes'),
            (fs.precision, 'Numbers to nearest 10, percentage to nearest whole number'),
            (fs.url, 'http://www.dcsf.gov.uk/rsgateway/DB/SFR/s000859/index.shtml'),
            (fs.taxonomy_url, '', ''),
            (fs.department, 'Department for Children, Schools and Families'),
            (fs.agency, '', ''),
            (fs.author, 'DCSF Data Services Group'),
            (fs.author_email, 'statistics@dcsf.gsi.gov.uk'),
            (fs.maintainer, '', ''),
            (fs.maintainer_email, '', ''),
            (fs.license_id, u'OKD Compliant::UK Open Government Licence (OGL)'),
            ]
        for vals in expected_values:
            if len(vals) == 2:
                field, expected_render_str = vals
                expected_render_readonly_str = vals[1]
            else:
                field, expected_render_str, expected_render_readonly_str = vals
            if isinstance(field.renderer, ckan.forms.common.SuggestedTextExtraField.SelectRenderer):
                if expected_render_str.startswith('other='):
                    expected_render_str = 'other" type="text" value="' + expected_render_str.strip('other=')
                    expected_render_readonly_str = expected_render_readonly_str.strip('other=')
                else:
                    # multiple choice must have the particular one selected
                    expected_render_str = 'selected" value="' + expected_render_str
            render = field.render()
            render_readonly = field.render_readonly()
            if expected_render_str == '':
                assert 'value=""' in render or 'value' not in render, \
                   'Expected a blank value in render of field %s but got \'%s\'' % \
                   (field.name, render)
            elif expected_render_str:
                assert expected_render_str in render, \
                       'Expected \'%s\' in render of field %s but got \'%s\'' % \
                       (expected_render_str, field.name, render)
            assert expected_render_readonly_str in render_readonly, \
                   'Expected \'%s\' in render_readonly of field %s but got \'%s\'' % \
                   (expected_render_readonly_str, field.name, render_readonly)
        self.check_tag(fs.geographic_coverage.render(), 'geographic_coverage-england', 'value="True"')
        self.check_tag(fs.temporal_coverage.render(), 'temporal_coverage-from', 'value="12:30 24/6/2008"')
        self.check_tag(fs.temporal_coverage.render(), 'temporal_coverage-to', 'value="6/2009"')

    def test_2_field_department_selected(self):
        fs = get_fieldset()
        pkg = model.Package.by_name(u'private-fostering-england-2009')
        fs = fs.bind(pkg)

        dept = fs.department.render()
        assert '<select' in dept, dept
        self.check_tag(dept, 'option', 'value="Department for Children, Schools and Families"', 'selected')
        assert 'option value="other">' in dept, dept
        assert 'Other:' in dept, dept
        assert 'value=""' in dept, dept

        dept_readonly = fs.department.render_readonly()
        assert 'Department for Children, Schools and Families' in dept_readonly, dept_readonly
        assert 'Other' not in dept_readonly, dept_readonly

    def test_2_field_department_none(self):
        # Create package
        model.repo.new_revision()
        pkg = model.Package(name=u'test3')
        model.Session.add(pkg)
        model.repo.commit_and_remove()
        CreateTestData.flag_for_deletion(pkg_names=[u'test3'])

        pkg = model.Package.by_name(u'test3')
        fs = get_fieldset()
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        dept = fs.department.render()
        dept_readonly = fs.department.render_readonly()
        assert '<select' in dept, dept
        assert '<option selected="selected" value=""></option>' in dept, dept
        assert '<p></p>' == dept_readonly, dept_readonly

    def test_2_field_department_other(self):
        # Create package
        model.repo.new_revision()
        pkg = model.Package(name=u'test2')
        model.Session.add(pkg)
        pkg.extras = {u'department':u'Not on the list'}
        model.repo.commit_and_remove()
        CreateTestData.flag_for_deletion(pkg_names=[u'test2'])

        pkg = model.Package.by_name(u'test2')
        fs = get_fieldset()
        fs = fs.bind(pkg)
        out = fs.render()
        assert out
        dept = fs.department.render()
        dept_readonly = fs.department.render_readonly()
        assert '<select' in dept, dept
        self.check_tag(dept, 'option', 'value="Department for Children, Schools and Families"', '!selected')
        self.check_tag(dept, 'option', 'value="other"', 'selected')
        assert 'Other:' in dept, dept
        assert 'value="Not on the list"' in dept, dept
        assert '<p>Not on the list</p>' == dept_readonly, dept_readonly

    def test_3_restrict(self):
        fs = get_fieldset(restrict=1)
        restricted_fields = ('name', 'department', 'national_statistic')
        for field_name in restricted_fields:
            assert getattr(fs, field_name)._readonly, getattr(fs, field_name)
        
    def test_4_sync_new(self):
        newtagname = 'newtagname'
        indict = _get_blank_param_dict(fs=get_fieldset())
        prefix = 'Package--'
        indict[prefix + 'name'] = u'testname'
        indict[prefix + 'title'] = u'testtitle'
        indict[prefix + 'notes'] = u'some new notes'
        indict[prefix + 'tags'] = u'russian tolstoy, ' + newtagname,
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
        indict[prefix + 'department'] = u'testdept'
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
            'geographic_coverage':'101000: England, Wales',
            'temporal_granularity':indict[prefix + 'temporal_granularity'],
            'temporal_coverage-from':'2008-06',
            'temporal_coverage-to':'2009-06',
            'national_statistic':'yes',
            'precision':indict[prefix + 'precision'],
            'taxonomy_url':indict[prefix + 'taxonomy_url'],
            'department':indict[prefix + 'department'],
            'agency':indict[prefix + 'agency'],
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
              'geographic_coverage':'111000: England, Scotland, Wales',
              'temporal_granularity':'testtempgran',
              'temporal_coverage-from':'2007-01-08',
              'temporal_coverage-to':'2007-01-09',
              'national_statistic':'yes',
              'precision':'testprec',
              'taxonomy_url':'testtaxurl',
              'department':'dosac',
              'agency':'testagency',
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
        indict[prefix + 'department'] = u'testdept'
        indict[prefix + 'agency'] = u'Quango 1'
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
            'geographic_coverage':'101000: England, Wales',
            'temporal_granularity':indict[prefix + 'temporal_granularity'],
            'temporal_coverage-from':'2008-06',
            'temporal_coverage-to':'2009-06',
            'national_statistic':'yes',
            'precision':indict[prefix + 'precision'],
            'taxonomy_url':indict[prefix + 'taxonomy_url'],
            'department':indict[prefix + 'department'],
            'agency':indict[prefix + 'agency'],            
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
              'department':'dosac',
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
        indict[prefix + 'department'] = u'testdept'
        # don't supply national_statistic param at all
        fs = get_fieldset(restrict=1).bind(pkg, data=indict)
        CreateTestData.flag_for_deletion(new_name)
        
        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

        assert not model.Package.by_name(new_name) # unchanged
        outpkg = model.Package.by_name(pkg_name) # unchanged
        assert outpkg
        # test sync worked
        assert outpkg.notes == indict[prefix + 'notes']

        # test gov fields
        extra_keys = outpkg.extras.keys()
        reqd_extras = {
            'national_statistic':'yes', # unchanged
            'department':init_data[0]['extras']['department'], # unchanged
            }
        for reqd_extra_key, reqd_extra_value in reqd_extras.items():
            assert reqd_extra_key in extra_keys, 'Key "%s" not found in extras %r' % (reqd_extra_key, extra_keys)
            assert outpkg.extras[reqd_extra_key] == reqd_extra_value, \
                 'Extra %s should equal %s but equals %s' % \
                 (reqd_extra_key, reqd_extra_value,
                  outpkg.extras[reqd_extra_key])

    def test_7_validate_bad_date(self):
        # bad dates must be picked up in validation
        indict = _get_blank_param_dict(fs=get_fieldset())
        prefix = 'Package--'
        indict[prefix + 'name'] = u'testname3'
        indict[prefix + 'title'] = u'Test'
        indict[prefix + 'department'] = u'abc'
        indict[prefix + 'notes'] = u'abcd'
        indict[prefix + 'license_id'] = u'abcde'
        indict[prefix + 'date_released'] = u'27/11/2008'
        fs = get_fieldset().bind(model.Package, data=indict, session=model.Session)

        validation = fs.validate()
        assert validation, validation

        indict[prefix + 'date_released'] = u'27/11/0208'
        fs = get_fieldset().bind(model.Package, data=indict, session=model.Session)
        validation = fs.validate()
        assert not validation

        # make sure it syncs without exception (this is req'd for a preview)
        model.repo.new_revision()
        fs.sync()
        model.repo.commit_and_remove()

    def test_8_geo_coverage(self):
        # create initial package
        pkg_name = u'test_coverage'
        init_data = [{
            'name':pkg_name,
            'title':'test_title',
            'extras':{
              'geographic_coverage':'001000: England, Scotland, Wales',
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
        self.assert_equal(outpkg.extras['geographic_coverage'], '111001: Global, Great Britain (England, Scotland, Wales)')

