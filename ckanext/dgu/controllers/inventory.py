import os
import csv
import json

from pylons import response, config
from ckan import model
from ckan.model.types import make_uuid
from ckan.lib.helpers import Page, flash_notice
from ckan.lib.base import h, BaseController, abort
from ckanext.dgu.lib.publisher import go_down_tree
from ckanext.dgu.plugins_toolkit import (render, c, request, _,
    ObjectNotFound, NotAuthorized, ValidationError, get_action, check_access)

import ckanext.dgu.lib.inventory as inventory_lib


class InventoryController(BaseController):

    def read(self, id):
        """ """
        return "The inventory homepage for {0}".format(id)

    def index(self):
        """
        This is the inventory homepage for when users want to drill-down through *just*
        the inventory on a per-publisher basis.
        """
        return "index"

    def edit(self, id):
        """
        The edit homepage to allow department admins to download and
        upload their inventories
        """

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        try:
            c.group_dict = get_action('group_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            self._redirect_if_previous_name(id)
            abort(404, 'Group not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('group_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to view internal inventory' % (c.user))

        self._get_group_info()
        return render('inventory/edit.html')


    def upload_status(self, id, upload_id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        try:
            c.group_dict = get_action('group_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            self._redirect_if_previous_name(id)
            abort(404, 'Group not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('group_update', context)
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
            c.group_dict = get_action('group_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            abort(404, 'Group not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('group_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to upload inventory' % (c.user))

        self._get_group_info()

        c.job_id = c.jobs[0][0]
        c.job_timestamp = c.jobs[0][1]

        return render('inventory/upload.html')

    def upload(self, id):
        """
        Upload of an inventory file, accepts a POST request with a file and
        then renders the result of the import to the user.
        """
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        try:
            c.group_dict = get_action('group_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            abort(404, 'Group not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('group_update', context)
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
        jobdict = c.group.extras.get('inventory.jobs', {})
        jobdict[job_id] = timestamp

        # Update the jobs list for this group
        c.group.extras['inventory.jobs'] = jobdict
        model.repo.new_revision()
        model.Session.add(c.group)
        model.Session.commit()

        return h.redirect_to( controller="ckanext.dgu.controllers.inventory:InventoryController",
                action="upload_complete", id=c.group.name)

    def _get_group_info(self):
        """ Helper to get group information to be shown on each page """
        c.group_admins = self.authorizer.get_admins(c.group)
        c.body_class = "group view"

        c.administrators = c.group.members_of_type(model.User, 'admin')
        c.editors = c.group.members_of_type(model.User, 'editor')
        c.restricted_to_publisher = 'publisher' in request.params
        parent_groups = c.group.get_groups('publisher')
        c.parent_publisher = parent_groups[0] if len(parent_groups) > 0 else None
        c.group_extras = []
        for extra in sorted(c.group_dict.get('extras',[]), key=lambda x:x['key']):
            if extra.get('state') == 'deleted':
                continue
            k, v = extra['key'], extra['value']
            v = json.loads(v)
            c.group_extras.append((k, v))
        c.group_extras = dict(c.group_extras)

        c.jobs = [(k, v,) for k,v in c.group.extras.get('inventory.jobs', {}).iteritems()]
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
            c.group_dict = get_action('group_show')(context, {"id": id})
            c.group = context['group']
        except ObjectNotFound:
            self._redirect_if_previous_name(id)
            abort(404, 'Group not found')
        except NotAuthorized:
            abort(401, 'Unauthorized to read group %s' % id)

        try:
            context['group'] = c.group
            check_access('group_update', context)
        except NotAuthorized, e:
            abort(401, 'User %r not authorized to download inventory'% (c.user))

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

