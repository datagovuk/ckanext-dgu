import os
import csv
import json
from urllib import urlencode

from pylons import response, config
from ckan import model
from ckan.model.types import make_uuid
from ckan.lib.base import h, BaseController, abort
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckanext.dgu.lib.publisher import go_down_tree
from ckan.lib.search import SearchIndexError
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckanext.dgu.plugins_toolkit import (render, c, request, _,
    ObjectNotFound, NotAuthorized, ValidationError, get_action, check_access)

import ckanext.dgu.lib.inventory as inventory_lib


def _encode_params(params):
    return [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v)) \
                                  for k, v in params]

def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)

def search_url(params):
    url = h.url_for(controller='ckanext.dgu.controllers.inventory:InventoryController', action='search')
    return url_with_params(url, params)


# TODO rename this 'UnpublishedController'
class InventoryController(BaseController):


    def _save_edit(self, name_or_id, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.POST))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = name_or_id

            pkg = get_action('package_update')(context, data_dict)
            c.pkg = context['package']
            c.pkg_dict = pkg
            h.redirect_to(controller='package', action='read', id=pkg['name'])
        except NotAuthorized:
            abort(401, 'Not authorized to save package')
        except ObjectNotFound, e:
            abort(404, _('Dataset not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except SearchIndexError, e:
            try:
                exc_str = unicode(repr(e.args))
            except:
                exc_str = unicode(str(e))
            abort(500, _(u'Unable to update search index.') + exc_str)
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit_item(name_or_id, data_dict, errors, error_summary)

    def edit_item(self, id, data=None, errors=None, error_summary=None):
        """
        Allows for the editing of a single item
        """
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'save': 'save' in request.params}

        if context['save'] and not data:
            return self._save_edit(id, context)

        try:
            c.pkg_dict = get_action('package_show')(context, {'id': id})
            context['for_edit'] = True

            old_data = get_action('package_show')(context, {'id': id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            data = data or old_data
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except ObjectNotFound:
            abort(404, _('Dataset not found'))

        c.pkg = context.get("package")

        try:
            check_access('package_update',context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.errors_json = json.dumps(errors)

        #self._setup_template_variables(context, {'id': package_id}, package_type=package_type)

        c.form = render('inventory/edit_form.html', extra_vars=vars)

        return render('inventory/edit_item.html')


    def edit(self, id):
        """
        The edit homepage to allow department admins to download and
        upload their inventories
        """

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        try:
            c.group_dict = get_action('organization_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            abort(404, 'Organisation not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('organization_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to view internal unpublished' % (c.user))

        self._get_group_info()
        return render('inventory/edit.html')


    def upload_status(self, id, upload_id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        try:
            c.group_dict = get_action('organization_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            abort(404, 'Group not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('organization_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to view internal inventory' % (c.user))

        self._get_group_info()

        root = model.Session.query(model.TaskStatus).filter(model.TaskStatus.id==upload_id).first()
        if not root:
            abort(404, 'Upload details not found')

        tasks = model.Session.query(model.TaskStatus).filter(model.TaskStatus.entity_id==root.entity_id).all()

        c.task = root
        c.task.packages = None

        for t in tasks:
            # Looks for a completed version with errors and stuff
            if t.state == 'Complete':
                c.task = t

                if t.error:
                    c.task.error = json.loads(t.error)

                if t.value:
                    c.task.packages = json.loads(t.value)

        return render('inventory/status.html')

    def upload_complete(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        try:
            c.group_dict = get_action('organization_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            abort(404, 'Group not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('organization_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to upload unpublished' % (c.user))

        self._get_group_info()

        c.job_id = c.jobs[0][0]
        c.job_timestamp = c.jobs[0][1]

        return render('inventory/upload.html')

    def upload(self, id):
        """
        Upload of an unpublished file, accepts a POST request with a file and
        then renders the result of the import to the user.
        """
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        try:
            c.group_dict = get_action('organization_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            abort(404, 'Organization not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('organization_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to upload inventory' % (c.user))

        if not 'upload' in request.POST or not hasattr(request.POST['upload'], "filename"):
            h.flash_error("No file was selected, please choose a file before uploading", allow_html=True)
            return h.redirect_to( controller="ckanext.dgu.controllers.inventory:InventoryController",
                action="edit", id=c.group.name)

        incoming = request.POST['upload'].filename
        file_root = config.get('inventory.temporary.storage', '/tmp')
        filename = os.path.join(file_root, make_uuid()) + "-{0}".format(incoming)

        with inventory_lib.UploadFileHelper(incoming, request.POST['upload'].file) as f:
            open(filename, 'wb').write(f.read())


        job_id, timestamp = inventory_lib.enqueue_document(c.userobj, filename, c.group)
        jobdict = json.loads(c.group.extras.get('inventory.jobs', '{}'))
        jobdict[job_id] = timestamp

        # Update the jobs list for this group
        # inventory.jobs will become a str when dictized, so serialize now.
        c.group.extras['inventory.jobs'] = json.dumps(jobdict)
        model.repo.new_revision()
        model.Session.add(c.group)
        model.Session.commit()

        return h.redirect_to( controller="ckanext.dgu.controllers.inventory:InventoryController",
                action="upload_complete", id=c.group.name)

    def _get_group_info(self):
        """ Helper to get group information to be shown on each page """
        from urllib import quote

        c.group_admins = c.group.members_of_type(model.User, 'admin')
        c.body_class = "group view"

        c.administrators = c.group.members_of_type(model.User, 'admin')
        c.editors = c.group.members_of_type(model.User, 'editor')
        c.restricted_to_publisher = 'publisher' in request.params
        parent_groups = c.group.get_parent_groups(type='organization')
        c.parent_publisher = parent_groups[0] if len(parent_groups) > 0 else None
        c.group_extras = []
        for extra in sorted(c.group_dict.get('extras',[]), key=lambda x:x['key']):
            if extra.get('state') == 'deleted':
                continue
            k, v = extra['key'], extra['value']
            #v = json.loads(v)
            c.group_extras.append((k, v))
        c.group_extras = dict(c.group_extras)

        c.group.encoded_title = quote(c.group.title)

        c.jobs = [(k, v,) for k,v in json.loads(c.group.extras.get('inventory.jobs', '{}')).iteritems()]
        c.jobs = sorted(c.jobs, key=lambda x: x[1], reverse=True)



    def download(self, id):
        """
        Downloads all of the current datasets for a given publisher as a read-only
        CSV file.
        """
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'group': id}

        try:
            c.group_dict = get_action('organization_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            abort(404, 'Organization not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read Organization %s' % id)

        try:
            context['group'] = c.group
            check_access('organization_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to download unpublished '% (c.user))

        groups = [c.group]
        if request.params.get('include_sub') == 'true':
            groups = go_down_tree(c.group)

        # Set the content-disposition so that it downloads the file
        # response.headers['Content-Type'] = "text/plain; charset=utf-8"
        response.headers['Content-Type'] = "text/csv; charset=utf-8"
        response.headers['Content-Disposition'] = str('attachment; filename=%s-inventory.csv' % (c.group.name,))

        writer = csv.writer(response)
        inventory_lib.render_inventory_header(writer)
        for gp in groups:
            ds = gp.members_of_type(model.Package).all()
            inventory_lib.render_inventory_row(writer, ds, gp)

