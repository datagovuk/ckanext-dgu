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
from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )


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

        # TODO: Fix this up, we only really need to do this when we are
        # showing the hierarchy (and then we should load on demand really).
        c.all_groups = model.Session.query(model.Group).\
                       filter(model.Group.type == 'publisher').order_by('title')
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
            return self.apply(group.id, data=data, errors=errors,
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

    def apply(self, id=None, data=None, errors=None, error_summary=None):
        """
        A user has requested access to this publisher and so we will send an
        email to any admins within the publisher.
        """
        if 'parent' in request.params and not id:
            id = request.params['parent']

        if id:
            c.group = model.Group.get(id)
            if 'save' in request.params and not errors:
                return self._send_application(c.group, request.params.get('reason', None))

        self._add_publisher_list()
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data.update(request.params)

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('publishers/apply_form.html', extra_vars=vars)

        return render('publishers/apply.html')

    def _add_publisher_list(self):
        c.possible_parents = model.Session.query(model.Group).\
               filter(model.Group.state == 'active').\
               filter(model.Group.type == 'publisher').\
               order_by(model.Group.title).all()

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

        # Temporary cleanup of a capacity being sent without a name
        users = [d for d in data_dict['users'] if len(d) == 2]
        data_dict['users'] = users

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



    def read(self, id):
        from ckan.lib.search import SearchError
        import genshi

        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema(group_type=type)}
        data_dict = {'id': id}
        q = c.q = request.params.get('q', '') # unicode format (decoded from utf8)

        try:
            c.group_dict = get_action('group_show')(context, data_dict)
            c.group = context['group']
        except NotFound:
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        # Search within group
        q += ' parent_publishers: "%s"' % c.group_dict.get('name')

        try:
            description_formatted = ckan.misc.MarkdownFormat().to_html(c.group_dict.get('description',''))
            c.description_formatted = genshi.HTML(description_formatted)
        except Exception, e:
            error_msg = "<span class='inline-warning'>%s</span>" % _("Cannot render description")
            c.description_formatted = genshi.HTML(error_msg)

        c.group_admins = self.authorizer.get_admins(c.group)

        context['return_query'] = True

        limit = 20
        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k,v in request.params.items() if k != 'page']

        def search_url(params):
            pubctrl = 'ckanext.dgu.controllers.publisher:PublisherController'
            url = h.url_for(controller=pubctrl, action='read', id=c.group_dict.get('name'))
            params = [(k, v.encode('utf-8') if isinstance(v, basestring) else str(v)) \
                            for k, v in params]
            return url + u'?' + urlencode(params)

        def drill_down_url(**by):
            params = list(params_nopage)
            params.extend(by.items())
            return search_url(set(params))

        c.drill_down_url = drill_down_url

        def remove_field(key, value):
            params = list(params_nopage)
            if (key, value) in params:
                params.remove((key, value))
            return search_url(params)

        c.remove_field = remove_field

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            c.fields = []
            search_extras = {}
            for (param, value) in request.params.items():
                if not param in ['q', 'page'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        q += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value

            data_dict = {
                'q':q,
                'facet.field':g.facets,
                'rows':limit,
                'start':(page-1)*limit,
                'extras':search_extras
            }

            query = get_action('package_search')(context,data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.facets = query['facets']
            c.page.items = query['results']
        except SearchError, se:
            log.error('Group search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])

        # Add the group's activity stream (already rendered to HTML) to the
        # template context for the group/read.html template to retrieve later.
        c.group_activity_stream = \
                ckan.logic.action.get.group_activity_list_html(context,
                    {'id': c.group_dict['id']})

        c.body_class = "group view"
        c.is_superuser_or_groupmember = c.userobj and \
                                        (Authorizer().is_sysadmin(unicode(c.user)) or \
                            len( set([c.group]).intersection( set(c.userobj.get_groups('publisher','admin')) ) ) > 0 )

        c.administrators = c.group.members_of_type(model.User, 'admin')
        c.editors = c.group.members_of_type(model.User, 'editor')

        c.restricted_to_publisher = 'publisher' in request.params

        return render('publishers/read.html')


    def report(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        query = """SELECT * FROM public.user WHERE id NOT IN
                (SELECT table_id FROM public.member WHERE table_name='user');"""
        c.unassigned_users = model.Session.query(model.User).from_statement(query).all()
        c.unassigned_users_count = len(c.unassigned_users)


        g_query = """SELECT g.* FROM public.group g WHERE id NOT IN
                    (SELECT group_id FROM public.member WHERE capacity='admin')
                    ORDER BY g.name;"""
        c.non_admin = model.Session.query(model.Group).from_statement(g_query).all()
        c.non_admin_count = len(c.non_admin)

        return render('publishers/report.html')


    def new(self, data=None, errors=None, error_summary=None):
        c.body_class = "group new"
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)
        self._add_publisher_list()

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
            c.is_superuser_or_groupadmin = True
        except NotAuthorized:
            c.is_superuser_or_groupadmin = False

        return super(PublisherController, self).new(data, errors, error_summary)
