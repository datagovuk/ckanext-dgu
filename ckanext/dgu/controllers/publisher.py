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

    def edit(self, id):
        c.body_class = "group edit"
        group = model.Group.get(id)
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'group': group}
        try:
            check_access('group_update', context)
            c.is_superuser_or_groupadmin = True
        except NotAuthorized:
            c.is_superuser_or_groupadmin = False
        return super(PublisherController, self).edit(id)


    def read(self, id):
        c.body_class = "group view"
        group = model.Group.get(id)
        c.is_superuser_or_groupmember = Authorizer().is_sysadmin(unicode(c.user)) or \
                len( set([group]).intersection( set(c.userobj.get_groups('publisher')) ) ) > 0
        return super(PublisherController, self).read(id)


    def new(self, data=None, errors=None, error_summary=None):
        if not Authorizer().is_sysadmin(unicode(c.user)):
            abort(401, _('Only system administrators can see this page'))
        c.body_class = "group new"
        return super(PublisherController, self).new(data, errors, error_summary)
