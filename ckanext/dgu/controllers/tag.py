from ckan.controllers.tag import TagController as BaseTagController
from ckan import model
from ckan.lib.helpers import AlphaPage, Page
from ckanext.dgu.plugins_toolkit import render, c, request, _, ObjectNotFound, NotAuthorized, ValidationError, get_action, check_access

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
            page = int(request.params.get('page', 1))
            data_dict['q'] = c.q
            data_dict['limit'] = LIMIT
            data_dict['offset'] = (page-1)*LIMIT
            data_dict['return_objects'] = True
               
        results = get_action('tag_list')(context,data_dict)
         
        if c.q:
            c.page = h.Page(
                            collection=results,
                            page=page,
                            item_count=len(results),
                            items_per_page=LIMIT
                            )
            c.page.items = results
        else:
            c.page = AlphaPage(
                collection=results,
                page=request.params.get('page', 'A'),
                alpha_attribute='name',
                other_text=_('Other'),
                controller_name='ckanext.dgu.controllers.tag:TagController',
            )

        return render('tag/index.html')
