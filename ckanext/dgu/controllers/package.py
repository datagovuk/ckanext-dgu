import urllib2
import logging
from urllib import quote
from urllib2 import HTTPError, URLError

from ckan.lib.base import render, c, model, abort, request, response, _, h, BaseController
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import get_action, check_access
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid, DataError
from ckanext.dgu.schema import GeoCoverageType
from ckan.lib.navl.dictization_functions import missing
import ckan.controllers.package

log = logging.getLogger(__name__)

class PackageController(ckan.controllers.package.PackageController):

    def history(self, id):
        """ Auth is different for DGU than for publisher default """
        # TODO Replace user names with department names
        return super(PackageController, self).history(id)

    def delete(self, id):
        """Provide a delete action, but only for UKLP datasets"""
        from ckan.lib.search import SearchIndexError
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user,
        }

        pkg_dict = get_action('package_show')(context, {'id':id}) # has side-effect of populating context.get('package')

        if request.params: # POST
            try:
                package_name = pkg_dict['name']
                get_action('package_delete')(context, {'id':id})
                h.flash_success(_('Successfully deleted package.'))
                self._form_save_redirect(package_name, 'edit')
            except NotAuthorized:
                abort(401, _('Unauthorized to read package %s') % id)
            except NotFound, e:
                abort(404, _('Package not found'))
            except DataError:
                abort(400, _(u'Integrity Error'))
            except SearchIndexError, e:
                abort(500, _(u'Unable to update search index.') + repr(e.args))
            except ValidationError, e:
                abort(400, _('Unable to delete package.') + repr(e.error_dict))

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
        return self._read_url('http://dgu-dev.okfn.org/comment/get/%s' % quote(id))

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
