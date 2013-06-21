import urllib2
import logging
from urllib import quote
from urllib2 import HTTPError, URLError

from ckan.lib.base import model, abort, response, h, BaseController
from ckanext.dgu.plugins_toolkit import render, c, request, _, ObjectNotFound, NotAuthorized, ValidationError, get_action, check_access
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid, DataError
from ckanext.dgu.schema import GeoCoverageType
from ckan.lib.navl.dictization_functions import missing
import ckan.controllers.package
from ckanext.dgu.lib.helpers import get_from_flat_dict
from ckan.lib.package_saver import PackageSaver

log = logging.getLogger(__name__)

class PackageController(ckan.controllers.package.PackageController):

    def history(self, id):
        """ Auth is different for DGU than for publisher default """
        # TODO Replace user names with department names
        return super(PackageController, self).history(id)

    def release(self, id, release_name=None):
        """ Shows all of the resources for a specific release should they
            be available """
        if not release_name:
            release_name = ''

        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
        }

        pkg = None
        try:
            c.pkg_dict = get_action('package_show')(context, {'id':id})
            c.pkg = context['package']
            #c.resources_json = json.dumps(c.pkg_dict.get('resources',[]))
        except ObjectNotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        resources_dicts = []
        for dct in c.pkg_dict['resources'][:]:
            if dct['resource_type'] == 'documentation':
                continue

            if dct['release_date'] == release_name:
                resources_dicts.append(dct)

        c.pkg_dict['resources'] = resources_dicts

        c.include_template = "release.html"
        c.sub_heading = "ONS Release: {0}".format(release_name or "No name")
        PackageSaver().render_package(c.pkg_dict, context)        
        return render("package/read.html")


    def delete(self, id):
        """Provide a delete ('withdraw') action, but only for UKLP datasets"""
        from ckan.lib.search import SearchIndexError
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
        }

        try:
            pkg_dict = get_action('package_show')(context, {'id':id}) # has side-effect of populating context.get('package')
        except NotAuthorized:
            abort(401, 'Not authorized to delete package')

        if request.params: # POST
            if 'cancel' in request.params:
                h.redirect_to(controller='package', action='read', id=id)
            elif 'delete' in request.params:
                try:
                    package_name = pkg_dict['name']
                    get_action('package_delete')(context, {'id':id})
                    is_uklp = get_from_flat_dict(pkg_dict['extras'], 'UKLP') == 'True'
                    if is_uklp:
                        action = 'withdrawn'
                        resource_type = get_from_flat_dict(pkg_dict['extras'], 'resource-type') + ' record'
                    else:
                        action = 'deleted'
                        resource_type = 'dataset'
                    h.flash_success('Successfully %s %s.' \
                                    % (action, resource_type))
                    self._form_save_redirect(package_name, 'edit')
                except NotAuthorized:
                    abort(401, _('Unauthorized to delete package %s') % id)
                except ObjectNotFound, e:
                    abort(404, _('Package not found'))
                except DataError:
                    abort(400, _(u'Integrity Error'))
                except SearchIndexError, e:
                    abort(500, _(u'Unable to update search index.') + repr(e.args))
                except ValidationError, e:
                    abort(400, _('Unable to delete package.') + repr(e.error_dict))
            else:
                abort(400, 'Parameter error')

        # GET
        c.pkg = context.get('package')
        try:
            check_access('package_delete', context)
        except NotAuthorized, e:
            abort(401, _('Unauthorized to delete package.'))
        package_type = self._get_package_type(id)
        self._setup_template_variables(context, {'id': id}, package_type=package_type)
        return render('package/delete.html')

class CommentProxy(BaseController):
    '''A proxy to Drupal on another server to provide comment HTML. Useful only
    for test purposes, when Drupal is not present locally.
    '''
    def get_comments(self, id):
        url = 'http://uat2.lampdevelopment.co.uk/comment/get/1c65c66a-fdec-4138-9c64-0f9bf087bcbb'
        #url = 'http://co-dev1.dh.bytemark.co.uk/comment/get/%s' % quote(id)
        return self._read_url(url)

    def _read_url(self, url, post_data=None, content_type=None):
        headers = {'Content-Type': content_type} if content_type else {}
        request = urllib2.Request(url, post_data, headers)
        try:
            f = urllib2.urlopen(request)
        except HTTPError, e:
            response.status_int = 400
            return 'Proxied server returned %s: %s' % (e.code, e.msg)
        except URLError, e:
            err = str(e)
            if 'Connection timed out' in err:
                response.status_int = 504
                return 'Proxied server timed-out: %s' % err
            raise e # Send an exception email to handle it better
        return f.read()
