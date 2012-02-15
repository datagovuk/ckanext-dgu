import logging
from urllib import urlencode

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import BaseController, c, model, request, render, h, g
from ckan.lib.base import ValidationException, abort, gettext
from pylons.i18n import get_lang, _
import ckan.authz as authz
from ckan.lib.alphabet_paginate import AlphaPage
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.authz import Authorizer
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.dictization.model_dictize import package_dictize
from ckan.controllers.group import GroupController
import ckan.forms
import ckan.model as model

log = logging.getLogger(__name__)



class PublisherController(GroupController):

    ## end hooks
    def index(self):

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        data_dict = {'all_fields': True}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        c.all_groups = model.Session.query(model.Group).\
                       filter(model.Group.type == 'publisher').order_by('title').all()

        c.page = AlphaPage(
            controller_name="ckanext.dgu.controllers.publisher:PublisherController",
            collection=c.all_groups,
            page=request.params.get('page', 'A'),
            alpha_attribute='title',
            other_text=_('-'),
        )

        return render('publishers/index.html')

    def _send_application( self, group, reason  ):
        from ckan.logic.action.update import group_error_summary
        from ckan.lib.mailer import mail_recipient
        from genshi.template.text import NewTextTemplate
        from pylons import config

        if not reason:
            h.flash_error(_("There was a problem with your submission, \
                             please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.apply(group.id, errors=errors,
                              error_summary=group_error_summary(errors))


        admins = group.members_of_type( model.User, 'admin' ).all()
        recipients = [(u.fullname,u.email) for u in admins] if admins else \
                     [(config.get('dgu.admin.name', "DGU Admin"),
                       config.get('dgu.admin.email', None), )]

        if not recipients:
            h.flash_error(_("There is a problem with the system configuration"))
            errors = {"reason": ["No group administrator exists"]}
            return self.apply(group.id, errors=errors,
                              error_summary=group_error_summary(errors))

        extra_vars = {
            'group'    : group,
            'requester': c.userobj,
            'reason'   : reason
        }
        email_msg = render("email/join_publisher_request.txt", extra_vars=extra_vars,
                         loader_class=NewTextTemplate)

        try:
            for (name,recipient) in recipients:
                mail_recipient(name,
                               recipient,
                               "Publisher request",
                               email_msg)
        except:
            h.flash_error(_("There is a problem with the system configuration"))
            errors = {"reason": ["No mail server was found"]}
            return self.apply(group.id, errors=errors,
                              error_summary=group_error_summary(errors))

        h.flash_success(_("Your application has been submitted"))
        h.redirect_to( 'publisher_read', id=group.name)

    def apply(self, id, data=None, errors=None, error_summary=None):
        """
        A user has requested access to this publisher and so we will send an
        email to any admins within the publisher.
        """
        c.group = model.Group.get(id)

        if 'save' in request.params and not errors:
            return self._send_application(c.group, request.params.get('reason', None))

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('publishers/apply_form.html', extra_vars=vars)

        return render('publishers/apply.html')

    def _add_users( self, group, parameters  ):
        from ckan.logic.schema import default_group_schema
        from ckan.lib.navl.dictization_functions import validate
        from ckan.lib.dictization.model_save import group_member_save

        if not group:
            h.flash_error(_("There was a problem with your submission, \
                             please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.apply(group.id, errors=errors,
                              error_summary=group_error_summary(errors))

        data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
        data_dict['id'] = group.id

        # Temporary fix for strange caching during dev
        l = data_dict['users']
        for d in l:
            if d['capacity'] == 'undefined':
                d['capacity'] = 'editor'

        context = {
            "group" : group,
            "schema": default_group_schema(),
            "model": model,
            "session": model.Session
        }

        model.repo.new_revision()
        group_member_save(context, data_dict, 'users')
        model.Session.commit()

        h.redirect_to( 'publisher_edit', id=group.name)


    def users(self, id, data=None, errors=None, error_summary=None):
        c.group = model.Group.get(id)
        context = {
                   'model': model,
                   'session': model.Session,
                   'user': c.user or c.author,
                   'group': c.group }

        try:
            check_access('group_update',context)
        except NotAuthorized, e:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        if 'save' in request.params and not errors:
            return self._add_users(c.group, request.params)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data['users'] = []
        data['users'].extend( { "name": user.name,
                                "capacity": "admin" }
                                for user in c.group.members_of_type( model.User, "admin"  ).all() )
        data['users'].extend( { "name": user.name,
                                "capacity": "editor" }
                                for user in c.group.members_of_type( model.User, 'editor' ).all() )

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('publishers/users_form.html', extra_vars=vars)

        return render('publishers/users.html')

    def edit(self, id):
        c.body_class = "group edit"

        group = model.Group.get(id)
        if not group:
            abort( 404 )
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'group': group}
        try:
            check_access('group_update', context)
            c.is_superuser_or_groupadmin = True
        except NotAuthorized:
            c.is_superuser_or_groupadmin = False

        c.possible_parents = model.Session.query(model.Group).\
               filter(model.Group.state == 'active').\
               filter(model.Group.type == 'publisher').\
               filter(model.Group.name != id ).order_by(model.Group.title).all()

        c.parent = None
        grps = group.get_groups('publisher')
        if grps:
            c.parent = grps[0]

        return super(PublisherController, self).edit(id)

    def read(self, id):
        c.body_class = "group view"
        group = model.Group.by_name(id)
        c.is_superuser_or_groupmember = c.userobj and \
                                        (Authorizer().is_sysadmin(unicode(c.user)) or \
                            len( set([group]).intersection( set(c.userobj.get_groups('publisher')) ) ) > 0 )

        c.administrators = group.members_of_type(model.User, 'admin')
        return super(PublisherController, self).read(id)


    def new(self, data=None, errors=None, error_summary=None):
        c.body_class = "group new"
        c.possible_parents = model.Session.query(model.Group).\
               filter(model.Group.state == 'active').\
               filter(model.Group.type == 'publisher').\
               order_by(model.Group.title).all()

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
            c.is_superuser_or_groupadmin = True
        except NotAuthorized:
            c.is_superuser_or_groupadmin = False

        return super(PublisherController, self).new(data, errors, error_summary)
