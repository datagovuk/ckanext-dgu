import os
import csv
import json

from pylons import response
from ckan import model
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

        self._get_group_info()
        c.messages = []
        with inventory_lib.UploadFileHelper(request.POST['upload'].filename, request.POST['upload'].file) as f:
            import messytables

            c.errors = []

            tableset = None
            try:
                _, ext = os.path.splitext( f.name )
                tableset = messytables.any_tableset(f,extension=ext[1:])
            except Exception, e:
                if str(e) == "Unrecognized MIME type: text/plain":
                    tableset = messytables.any_tableset(f, mimetype="text/csv")
                else:
                    c.errors.append("Unable to load file: {0}".format(e))

            if not tableset:
                c.errors.append("Unable to row data from uploaded file. Please contact a sysadmin.")
                return render('inventory/upload.html')

            first = True
            pos = 0
            for row in tableset.tables[0]:
                pos = pos + 1
                if first:
                    # Validate the header row to make sure it hasn't been modified
                    ok, msg = inventory_lib.validate_incoming_inventory_header(row)
                    if not ok:
                        c.errors.append("<strong>Upload error</strong>: {0}".format(msg))
                        break
                    first = False
                    continue

                try:
                    pkg, grp, pub_date, msg = inventory_lib.process_incoming_inventory_row(pos, row, c.group.name)
                    if pkg:
                        c.messages.append((pkg, grp, pub_date, msg,))
                except Exception, exc:
                    c.errors.append(str(exc))

            if pos < 2 and len(c.errors) == 0:
                c.errors.append("There was not enough data in the upload file")

        return render('inventory/upload.html')

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

