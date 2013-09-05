import logging
from urllib import urlencode
from urlparse import urljoin
from sqlalchemy.orm import eagerload_all
from ckanext.dgu.plugins_toolkit import c, request, render, _, ObjectNotFound, NotAuthorized, ValidationError, check_access, get_action
from ckan.lib.base import BaseController, model, h, g
from ckan.lib.base import abort, gettext
from pylons.i18n import get_lang
from ckan.lib.alphabet_paginate import AlphaPage
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.dictization.model_dictize import package_dictize
from ckan.controllers.group import GroupController
import ckan.model as model
from ckan.lib.helpers import json
from ckan.lib.navl.validators import (ignore_missing,
                                      not_empty,
                                      empty,
                                      ignore,
                                      keep_extras,
                                     )
from ckanext.dgu.lib.publisher import go_up_tree
from ckanext.dgu.authentication.drupal_auth import DrupalUserMapping
from ckanext.dgu.drupalclient import DrupalClient
from ckan.plugins import PluginImplementations, IMiddleware
from ckanext.dgu.plugin import DrupalAuthPlugin

log = logging.getLogger(__name__)

report_limit = 20

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
                       filter(model.Group.type == 'publisher').\
                       filter(model.Group.state == 'active').\
                       order_by('title')
        c.page = AlphaPage(
            controller_name="ckanext.dgu.controllers.publisher:PublisherController",
            collection=c.all_groups,
            page=request.params.get('page', 'A'),
            alpha_attribute='title',
            other_text=_('Other'),
        )

        return render('publisher/index.html')



    def _send_application( self, group, reason  ):
        from ckan.logic.action import error_summary
        from ckan.lib.mailer import mail_recipient
        from genshi.template.text import NewTextTemplate
        from pylons import config

        if not reason:
            h.flash_error(_("There was a problem with your submission, \
                             please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.apply(group.id, errors=errors,
                              error_summary=error_summary(errors))

        # look for publisher admins up the tree
        recipients = []
        recipient_publisher = None
        for publisher in go_up_tree(group):
            admins = publisher.members_of_type(model.User, 'admin').all()
            if admins:
                recipients = [(u.fullname,u.email) for u in admins]
                recipient_publisher = publisher.title
                break
        if not recipients:
            if not config.get('dgu.admin.email'):
                log.error('User "%s" prevented from applying for publisher access for "%s" '
                          'because: dgu.admin.email is not setup in CKAN config.',
                          c.user, group.name)
                h.flash_error(_("There is a problem with the system configuration"))
                errors = {"reason": ["%s does not have an administrator user to contact" % group.name]}
                return self.apply(group.id, data=data, errors=errors,
                                  error_summary=error_summary(errors))
            recipients = [(config.get('dgu.admin.name', "DGU Admin"),
                           config['dgu.admin.email'])]
            recipient_publisher = 'data.gov.uk admin'


        url = urljoin(g.site_url,
            h.url_for(controller='ckanext.dgu.controllers.publisher:PublisherController',
                      action='users', id=group.name))

        log.debug('User "%s" requested publisher access for "%s" which was sent to admin %s (%r) with reason: %r',
                  c.user, group.name, recipient_publisher, recipients, reason)
        extra_vars = {
            'group'    : group,
            'requester': c.userobj,
            'reason'   : reason,
            'accept_url': url
        }
        email_msg = render("email/join_publisher_request.txt", extra_vars=extra_vars,
                           loader_class=NewTextTemplate)

        try:
            for (name,recipient) in recipients:
                mail_recipient(name,
                               recipient,
                               "Publisher request",
                               email_msg)
        except Exception, e:
            h.flash_error(_("There is a problem with the system configuration"))
            errors = {"reason": ["No mail server was found"]}
            log.error('User "%s" prevented from applying for publisher access for "%s" because of mail configuration error: %s',
                      c.user, group.name, e)
            return self.apply(group.id, errors=errors,
                              error_summary=error_summary(errors))

        h.flash_success("Your application has been submitted to administrator for: %s" % recipient_publisher)
        h.redirect_to( 'publisher_read', id=group.name)

    def apply(self, id=None, data=None, errors=None, error_summary=None):
        """
        Form for a user to request to be an editor for a publisher.
        It sends an email to a suitable admin.
        """
        if not c.user:
            abort(401, _('You must be logged in to apply for membership'))

        if 'parent' in request.params and not id:
            id = request.params['parent']

        if id:
            c.group = model.Group.by_name(id)
            if not c.group:
                log.warning('Could not find publisher for name %s', id)
                abort(404, _('Publisher not found'))
            if 'save' in request.params and not errors:
                return self._send_application(c.group, request.params.get('reason', None))

        self._add_publisher_list()
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data.update(request.params)

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('publisher/apply_form.html', extra_vars=vars)
        return render('publisher/apply.html')


    def _add_publisher_list(self):
        c.possible_parents = model.Session.query(model.Group).\
               filter(model.Group.state == 'active').\
               filter(model.Group.type == 'publisher').\
               order_by(model.Group.title).all()

    def _add_users(self, group, parameters):
        from ckan.logic.schema import default_group_schema
        from ckan.logic.action import error_summary
        from ckan.lib.dictization.model_save import group_member_save

        if not group:
            h.flash_error(_("There was a problem with your submission, \
                             please correct it and try again"))
            errors = {"reason": ["No reason was supplied"]}
            return self.users(group.name, errors=errors,
                              error_summary=error_summary(errors))

        data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
        data_dict['id'] = group.id

        # Check that the user being added, if they are a Drupal user, has
        # verified their email address
        new_users = [user['name'] for user in data_dict['users'] \
                     if not 'capacity' in user or user['capacity'] == 'undefined']
        for user_name in new_users:
            drupal_id = DrupalUserMapping.ckan_user_name_to_drupal_id(user_name)
            if drupal_id:
                if not is_drupal_auth_activated():
                    # joint auth with Drupal is not activated, so cannot
                    # check with Drupal
                    log.warning('Drupal user made editor/admin but without checking email is verified.')
                    break
                if 'drupal_client' not in dir(self):
                    self.drupal_client = DrupalClient()
                user_properties = self.drupal_client.get_user_properties(drupal_id)
                roles = user_properties['roles'].values()
                if 'unverified user' in roles:
                    user = model.User.by_name(user_name)
                    h.flash_error("There was a problem with your submission - see the error message below.")
                    errors = {"reason": ['User "%s" has not verified their email address yet. '
                                         'Please ask them to do this and then try again. ' % \
                                          user.fullname]}
                    log.warning('Trying to add user (%r %s) who is not verified to group %s',
                                user.fullname, user_name, group.name)
                    # NB Other values in the form are lost, but that is probably ok
                    return self.users(group.name, errors=errors,
                                      error_summary=error_summary(errors))

        # Temporary fix for strange caching during dev
        l = data_dict['users']
        for d in l:
            # Form javascript creates d['capacity'] == 'undefined' for
            # newly added users.
            # If javascript in users form is not working (such as in tests)
            # it will not create a capacity value.
            if 'capacity' not in d or d['capacity'] == 'undefined':
                # default to 'editor'
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

        h.redirect_to('/publisher/%s' % str(group.name))


    def users(self, id, data=None, errors=None, error_summary=None):
        c.group = model.Group.by_name(id)

        if not c.group:
            abort(404, _('Group not found'))

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
        for capacity in ('admin', 'editor'):
            data['users'].extend(
                { "name": user.name,
                  "fullname": user.fullname,
                  "capacity": capacity }
                for user in c.group.members_of_type(model.User, capacity).all() )

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('publisher/users_form.html', extra_vars=vars)

        return render('publisher/users.html')

    def _redirect_if_previous_name(self, id):
        # If we can find id in the extras for any group we will use it
        # to re-direct the user to the new name for the group. If not then
        # we'll just let it fail.  If we find multiple groups with the name
        # we'll just redirect to the first match.
        import ckan.model as model

        match = model.Session.query(model.GroupExtra).\
            filter(model.GroupExtra.key.like('previous-name-%')).\
            filter(model.GroupExtra.value == id).\
            filter(model.GroupExtra.state=='active').order_by('key desc').first()
        if match:
            h.redirect_to( 'publisher_read', id=match.group.name)

    def read(self, id):
        from ckan.lib.search import SearchError
        import ckan.logic
        import genshi

        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema(group_type=type)}
        data_dict = {'id': id}
        q = c.q = request.params.get('q', '') # unicode format (decoded from utf8)
        fq = ''

        # TODO: Deduplicate this code copied from index()
        # We shouldn't need ALL of the groups to build a sub-tree, either
        # parent.get_children() (if there's a parent), or c.group.get_childen()
        # should be enough.  Rather than fix this, we should load the group
        # hierarchy dynamically
        c.all_groups = model.Session.query(model.Group).\
                       filter(model.Group.type == 'publisher').\
                       filter(model.Group.state == 'active').\
                       order_by('title')

        try:
            c.group_dict = get_action('group_show')(context, data_dict)
            c.group = context['group']
        except ObjectNotFound:
            self._redirect_if_previous_name(id)
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        # Search within group
        fq += ' parent_publishers: "%s"' % c.group_dict.get('name')

        description = c.group_dict.get('description','').replace('&amp;', '&')
        try:
            description_formatted = ckan.misc.MarkdownFormat().to_html(description)
            c.description_formatted = genshi.HTML(description_formatted)
        except Exception, e:
            error_msg = "<span class='inline-warning'>%s</span>" % _("Cannot render description")
            c.description_formatted = genshi.HTML(error_msg)

        context['return_query'] = True

        limit = 10
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
            params.remove((key, value))
            return search_url(params)

        c.remove_field = remove_field

        sort_by = request.params.get('sort', None)
        params_nosort = [(k, v) for k,v in params_nopage if k != 'sort']
        def _sort_by(fields):
            """
            Sort by the given list of fields.

            Each entry in the list is a 2-tuple: (fieldname, sort_order)

            eg - [('metadata_modified', 'desc'), ('name', 'asc')]

            If fields is empty, then the default ordering is used.
            """
            params = params_nosort[:]

            if fields:
                sort_string = ', '.join( '%s %s' % f for f in fields )
                params.append(('sort', sort_string))
            return search_url(params)
        c.sort_by = _sort_by
        if sort_by is None:
            c.sort_by_fields = []
        else:
            c.sort_by_fields = [ field.split()[0] for field in sort_by.split(',') ]

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)

        try:
            c.fields = []
            search_extras = {}
            for (param, value) in request.params.items():
                if not param in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        fq += ' %s: "%s"' % (param, value)
                    else:
                        search_extras[param] = value

            data_dict = {
                'q':q,
                'fq':fq,
                'facet.field':g.facets,
                'rows':limit,
                'start':(page-1)*limit,
                'sort': sort_by,
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
        #c.group_activity_stream = \
        #        ckan.logic.action.get.group_activity_list_html(context,
        #            {'id': c.group_dict['id']})

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
            # (Value is no longer in JSON, due to https://github.com/okfn/ckan/issues/381 )
            c.group_extras.append((k, v))
        c.group_extras = dict(c.group_extras)

        return render('publisher/read.html')


    def report_users_not_assigned_to_groups(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        query = """SELECT * FROM public.user WHERE id NOT IN
                (SELECT table_id FROM public.member WHERE table_name='user')
                ORDER BY created desc;"""
        c.unassigned_users = model.Session.query(model.User).from_statement(query).all()
        c.unassigned_users_count = len(c.unassigned_users)

        return render('publisher/report_users_not_assigned_to_groups.html')


    def report_groups_without_admins(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        g_query = """SELECT g.* FROM public.group g WHERE id NOT IN
                    (SELECT group_id FROM public.member WHERE capacity='admin')
                    ORDER BY g.name;"""
        c.non_admin = model.Session.query(model.Group).from_statement(g_query).all()
        c.non_admin_count = len(c.non_admin)

        return render('publisher/report_groups_without_admins.html')

    def report_publishers_and_users(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        q = model.Group.all('publisher')

        c.count = q.count()

        c.page = h.Page(
            collection=q,
            page=int(request.params.get('page', 1)),
            url=h.pager_url,
            items_per_page=report_limit,
            )

        return render('publisher/report_publishers_and_users.html')

    def report_users(self):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        q = model.Session.query(model.User).order_by(model.User.created.desc())
        c.count = q.count()

        c.page = h.Page(
            collection=q,
            page=int(request.params.get('page', 1)),
            url=h.pager_url,
            items_per_page=report_limit,
            )

        return render('publisher/report_users.html')

    def new(self, data=None, errors=None, error_summary=None):
        c.body_class = "group new"
        self._add_publisher_list()

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        try:
            check_access('group_create', context)
            c.is_superuser_or_groupadmin = True
        except NotAuthorized:
            c.is_superuser_or_groupadmin = False

        return super(PublisherController, self).new(data, errors, error_summary)

def is_drupal_auth_activated():
    '''Returns whether the DrupalAuthPlugin is activated'''
    return any(isinstance(plugin, DrupalAuthPlugin) for plugin in PluginImplementations(IMiddleware))
