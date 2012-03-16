import logging
from ckan.lib.base import render, c, model, abort, request, _, h
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import get_action, check_access
from ckan.lib.field_types import DateType, DateConvertError
from ckan.lib.navl.dictization_functions import Invalid, DataError
from ckanext.dgu.schema import GeoCoverageType
from ckan.lib.navl.dictization_functions import missing
from ckan.controllers.package import PackageController

log = logging.getLogger(__name__)

class PackageGov3Controller(PackageController):

    def history(self, id):
        """ Auth is different for DGU than for publisher default """
        if len ( c.userobj.get_groups('publisher') ) == 0:
            abort( 401, _('Unauthorized to read package history') )
        return super(PackageGov3Controller, self).history(  id )

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
