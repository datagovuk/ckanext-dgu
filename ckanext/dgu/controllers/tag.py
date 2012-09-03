from ckan.controllers.tag import TagController as BaseTagController
from ckan import model
from ckan.lib.helpers import Page
from ckan.lib.base import abort
from ckanext.dgu.lib.alphabet_paginate_large import AlphaPageLarge
from ckanext.dgu.plugins_toolkit import render, c, request, _, ObjectNotFound, NotAuthorized, ValidationError, get_action, check_access
from ckan.lib.base import h

LIMIT = 50

class TagController(BaseTagController):
    def index(self):
        c.q = request.params.get('q', '')

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        # This is the one difference from ckan core.
        # No need for all vocab / translation stuff, so save the massive
        # effort of dictizing every tag. This improves page load from
        # 60s to 10s.
        data_dict = {'all_fields': False} 

        if c.q:
            try:
                page = int(request.params.get('page', 1))
            except ValueError:
                abort(404, _('Not found'))
            data_dict['q'] = c.q
            data_dict['limit'] = LIMIT
            data_dict['offset'] = (page-1)*LIMIT
            data_dict['return_objects'] = True

            result_dict = get_action('tag_search')(context, data_dict)

            def pager_url(q=None, page=None):
                return h.url_for(controller='ckanext.dgu.controllers.tag:TagController', action='index', q=request.params['q'], page=page)
            c.page = h.Page(
                            collection=result_dict['results'],
                            page=page,
                            item_count=result_dict['count'],
                            items_per_page=LIMIT,
                            url=pager_url,
                            )
            c.page.items = [tag_dict['name'] for tag_dict in result_dict['results']]
        else:
            results = get_action('tag_list')(context, data_dict)

            c.page = AlphaPageLarge(
                collection=results,
                page=request.params.get('page', 'A'),
                alpha_attribute='name',
                other_text=_('Other'),
                controller_name='ckanext.dgu.controllers.tag:TagController',
            )

        return render('tag/index.html')

