import logging
from urllib import urlencode

from sqlalchemy.orm import eagerload_all
from ckan.lib.base import BaseController, c, model, request, render, h, g
from ckan.lib.base import ValidationException, abort, gettext
from pylons.i18n import get_lang, _
import ckan.authz as authz
from ckan.lib.alphabet_paginate import AlphaPage
from ckan.lib.navl.dictization_functions import DataError, unflatten, validate
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.lib.dictization.model_dictize import package_dictize
from ckan.controllers.group import GroupController
import ckan.forms
import ckan.model as model

log = logging.getLogger(__name__)

def demo_data(model):
    model.repo.new_revision()

    for x in range(0,10):
        model.Session.add( model.Group(name="group_%s" % x, title=u"Group %s" % x, type="publisher") )        
    model.Session.flush()
        
    g1 = model.Group.get('group_1')
    g2 = model.Group.get('group_2')
    g3 = model.Group.get('group_3')
    g4 = model.Group.get('group_4')                
    g5 = model.Group.get('group_5')
    g6 = model.Group.get('group_6')
    g7 = model.Group.get('group_7')                
        
    member1 = model.Member(group=g1, table_id=g2.id, table_name='group')
    member2 = model.Member(group=g1, table_id=g3.id, table_name='group')
    member3 = model.Member(group=g1, table_id=g4.id, table_name='group')
    member5 = model.Member(group=g2, table_id=g6.id, table_name='group')
    member6 = model.Member(group=g2, table_id=g7.id, table_name='group')                                
    member4 = model.Member(group=g2, table_id=g5.id, table_name='group')                
        
    model.Session.add(member1)        
    model.Session.add(member2)        
    model.Session.add(member3)        
    model.Session.add(member4)        
    model.Session.add(member5)        
    model.Session.add(member6)        
    model.Session.flush()
    

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
        
        # Testing junk until I can get the publisher new working again.
        results = []
        for x in range( 1, 25):
            results = results + [
                { "title": "ABC", "name": "alpha_beta_c", "packages": 1, "display_name": "ABC", "description": "A description"},
                { "title": "DEF", "name": "deaf",         "packages": 2, "display_name":  "DEF", "description": "A description"},
                { "title": "XYZ", "name": "xylophone",    "packages": 3, "display_name": "XYZ", "description": "A description" },                        
            ]

        c.page = AlphaPage(
            controller_name="ckanext.dgu.controllers.publisher:PublisherController",
            collection=results,
            page=request.params.get('page', 'A'),
            alpha_attribute='title',
            other_text=_('-'),
        )
        
        demo_data(model)
        c.all_groups = model.Session.query(model.Group).\
                       filter(model.Group.type == 'publisher').order_by('title').all()
        
        return render('publishers/index.html')

