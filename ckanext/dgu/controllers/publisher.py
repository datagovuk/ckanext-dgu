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
from ckan.controllers.organization import OrganizationController
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
from ckanext.dgu.forms.validators import categories
from ckanext.dgu.lib import helpers as dgu_helpers

log = logging.getLogger(__name__)

report_limit = 20

class PublisherController(OrganizationController):


    ## end hooks
    def index(self):

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        data_dict = {'all_fields': True}

        try:
            check_access('site_read', context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        # This used to be just used by the hierarchy but now is not, but it is
        # now used for search autocomplete and count.
        # c.all_groups = model.Session.query(model.Group).\
        #                filter(model.Group.type == 'organization').\
        #                filter(model.Group.state == 'active').\
        #                order_by('title')
        # c.page = AlphaPage(
        #     controller_name="ckanext.dgu.controllers.publisher:PublisherController",
        #     collection=c.all_groups,
        #     page=request.params.get('page', 'A'),
        #     alpha_attribute='title',
        #     other_text=_('Other'),
        # )

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
                errors = {"reason": ["data.gov.uk error"]}
                return self.apply(group.id, errors=errors,
                                  error_summary=error_summary(errors))
            recipients = [(config.get('dgu.admin.name', "DGU Admin"),
                           config['dgu.admin.email'])]
            recipient_publisher = 'data.gov.uk admin team'


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
                               subject='DGUKPublisherRequest: Please add me as a data.gov.uk publisher',
                               body=email_msg)
        except Exception, e:
            h.flash_error('There is a problem with the system configuration. Please instead <a href="http://data.gov.uk/contact">contact the data.gov.uk team</a>', allow_html=True)
            errors = {"reason": ["data.gov.uk error"]}
            log.error('User "%s" prevented from applying for publisher access for "%s" because of mail configuration error: %s',
                      c.user, group.name, e)
            return self.apply(group.id, errors=errors,
                              error_summary=error_summary(errors))

        h.flash_success('Your application has been submitted to administrator for: %s. If you do not hear back in a couple of days then <a href="http://data.gov.uk/contact">contact the data.gov.uk team</a>' % recipient_publisher, allow_html=True)
        h.redirect_to('publisher_read', id=group.name)

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
            c.group = model.Group.get(id)
            if not c.group:
                log.warning('Could not find publisher for name %s', id)
                abort(404, _('Publisher not found'))
            if 'save' in request.params and not errors:
                from ckanext.dgu.model.publisher_request import PublisherRequest

                reason = request.params.get('reason', None)

                if model.Session.query(PublisherRequest).filter_by(user_name=c.user, group_name=id).all():
                    h.flash_error('A request for this publisher is already in the system. If you have waited more than a couple of days then <a href="http://data.gov.uk/contact">contact the data.gov.uk team</a>', allow_html=True) 
                    h.redirect_to('publisher_apply', id=id)
                    return
                else:
                    req = PublisherRequest(user_name=c.user, group_name=id, reason=reason)
                    model.Session.add(req)
                    model.Session.commit()

                    return self._send_application(c.group, reason)
        else:
            c.possible_parents = model.Session.query(model.Group)\
                .filter(model.Group.state=='active').order_by(model.Group.title).all()

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}

        data.update(request.params)

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        c.form = render('publisher/apply_form.html', extra_vars=vars)
        return render('publisher/apply.html')


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

        group_type = self._get_group_type(id.split('@')[0])
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema(group_type=group_type),
                   'for_view': True}
        data_dict = {'id': id}

        try:
            # Do not query for the group datasets when dictizing, as they will
            # be ignored and get requested on the controller anyway
            context['include_datasets'] = False
            c.group_dict = get_action('organization_show')(context, data_dict)
            c.group = context['group']
        except ObjectNotFound:
            self._redirect_if_previous_name(id)
            abort(404, _('Group not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read group %s') % id)

        c.description = c.group_dict.get('description','').replace('&amp;', '&')
        context['return_query'] = True

        limit = 12
        try:
            page = int(request.params.get('page', 1))
        except ValueError, e:
            abort(400, ('"page" parameter must be an integer'))

        def pager_url(q=None, page=None):
            url = h.url_for(controller='ckanext.dgu.controllers.publisher:PublisherController', action='read', id=c.group_dict.get('name'))
            params = [('page', str(page))]
            return url + u'?' + urlencode(params)

        try:
            # Search within group
            fq = ' publisher: "%s"' % c.group_dict.get('name')
            data_dict = {
                'fq':fq,
                'rows':limit,
                'start':(page-1)*limit,
            }
            search_context = dict((k, v) for (k, v) in context.items() if k != 'schema')
            query = get_action('package_search')(search_context, data_dict)

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.page.items = query['results']
        except SearchError, se:
            log.error('Group search error: %r', se.args)
            c.query_error = True
            c.facets = {}
            c.page = h.Page(collection=[])

        c.administrators = c.group.members_of_type(model.User, 'admin')
        c.editors = c.group.members_of_type(model.User, 'editor')

        parent_groups = c.group.get_parent_groups(type='organization')
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

        q = model.Group.all('organization')

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

        return super(PublisherController, self).new(data, errors, error_summary)

    def publisher_request(self, token, decision=None):
        from ckan import model
        from ckanext.dgu.model.publisher_request import PublisherRequest

        try:
            c.req = model.Session.query(PublisherRequest).filter_by(login_token=token).one()
            c.req_user = model.Session.query(model.User).filter_by(name=c.req.user_name).one()
            c.req_group = model.Session.query(model.Group).filter_by(name=c.req.group_name).one()
            c.in_group = c.req_user.is_in_group(c.req_group.id)
        except Exception, ex:
            abort(404, 'Request not found')
 
        if decision:
            if decision not in ['reject', 'accept']:
                abort(400, 'Invalid Request')
            elif decision == 'reject':
                c.req.decision = False
                msg = 'The application of <strong>%s</strong> to the publisher <strong>%s</strong> was marked as rejected' % (c.req_user.fullname, c.req_group.title)
                # Should we remove the user from the group if
                # they have already been added?
            else:
                c.req.decision = True
                if not c.in_group:
                    model.repo.new_revision()
                    member = model.Member(group=c.req_group,
                                          table_id=c.req_user.id,
                                          table_name='user',
                                          capacity='editor')
                    model.Session.add(member)
                msg = '<strong>%s</strong> was added to the publisher <strong>%s</strong>' % (c.req_user.fullname, c.req_group.title)
            model.Session.commit()

            h.flash_success(msg, allow_html=True)
            h.redirect_to('publisher_request', token=token)
        else:
            return render('data/publisher_request.html')

    def publisher_requests(self):
        if not dgu_helpers.is_sysadmin():
            abort(401, 'User must be a sysadmin to view this page.')

        from ckan import model
        from ckanext.dgu.model.publisher_request import PublisherRequest

        publisher_requests = []
        for req in model.Session.query(PublisherRequest).order_by(PublisherRequest.date_of_request.desc()).all():
            item = {}
            item['user'] = model.Session.query(model.User).filter(model.User.name==req.user_name).one()
            item['group'] = model.Session.query(model.Group).filter(model.Group.name==req.group_name).one()
            item['decision'] = req.decision
            item['date_of_request'] = req.date_of_request
            item['date_of_decision'] = req.date_of_decision
            item['login_token'] = req.login_token
            publisher_requests.append(item)

        c.publisher_requests = publisher_requests
        return render('data/publisher_requests.html')

    def _group_form(self, group_type=None):
        return 'publisher/edit_form.html'

    def _new_template(self, group_type):
        return 'publisher/new.html'

    def _about_template(self, group_type):
        return 'publisher/about.html'

    def _index_template(self, group_type):
        return 'publisher/index.html'

    def _admins_template(self, group_type):
        return 'publisher/admins.html'

    def _read_template(self, group_type):
        return 'publisher/read.html'

    def _edit_template(self, group_type):
        return 'publisher/edit.html'

    def _guess_group_type(self, expecting_name=False):
        return 'organization'


    def _setup_template_variables(self, context, data_dict, group_type):
        """
        Add variables to c just prior to the template being rendered. We should
        use the available groups for the current user, but should be optional
        in case this is a top level group
        """
        c.body_class = "group edit"
        c.schema_fields = [
            'contact-name', 'contact-email', 'contact-phone',
            'foi-name', 'foi-email', 'foi-phone', 'foi-web',
                'category',
        ]

        if group_type=='organization':
            # editing an organization?
            group = context.get('group')

            c.parent = None
            if group:
                parents = group.get_parent_groups('organization')
                if parents:
                    c.parent = parents[0]

            model = context['model']
            group_id = data_dict.get('id')
            if group_id:
                group = model.Group.get(group_id)
                c.allowable_parent_groups = \
                    group.groups_allowed_to_be_its_parent(type='organization')
            else:
                c.allowable_parent_groups = model.Group.all(
                    group_type='organization')

            if group:
                c.users = group.members_of_type(model.User)

        else:
            # creating an organization
            c.body_class = 'group new'
            c.allowable_parent_groups = model.Group.all(
                group_type='organization')


        c.categories = categories

def is_drupal_auth_activated():
    '''Returns whether the DrupalAuthPlugin is activated'''
    return any(isinstance(plugin, DrupalAuthPlugin) for plugin in PluginImplementations(IMiddleware))
