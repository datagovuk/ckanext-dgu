import ckan.logic as logic
import ckanext.dgu.lib.basket as basket

import json

from lib.base import c, model, BaseController, abort, redirect, h
from pylons.i18n import _

_basket = basket.Basket(categories=('dataset',))

# --- Library interface to the basket --- #

def basket_contents():
    """
    Returns the list of pkg_dicts in the current basket.
    """
        
    context = {
        'model': model, 'session': model.Session,
        'user': c.user or c.author, 'for_view': True
    }

    dataset_ids = _basket.contents(category='dataset')
    datasets = [ logic.get_action('package_show')(context, {'id': id})\
                    for id in dataset_ids ]
    return datasets

# --- Basket Controller --- #

class BasketController(BaseController):

    def add_dataset_to_basket(self, id):
        """
        Add the given dataset to the backet.

        Returns json-dict representation of the basket's new contents
        """
        
        context = {
            'model': model, 'session': model.Session,
            'user': c.user or c.author, 'for_view': True
        }

        data_dict = {'id': id}

        # Check the package exists
        try:
            pkg_dict = logic.get_action('package_show')(context, data_dict)
        except logic.NotAuthorized:
            abort(401, _('Unauthorized to read package'))
        except logic.NotFound:
            abort(404, _('Dataset not found'))

        self._add_to_basket(pkg_dict['id'])
        redirect(self._basket_contents_url)

    def clear(self):
        """
        Clears the basket
        """
        _basket.clear(category='dataset')
        redirect(self._basket_contents_url)

    def contents(self):
        """
        Returns json representation of the basket's contents
        """
        try:
            return json.dumps(self._basket_contents)
        except logic.NotAuthorized:
            abort(401, _('Unauthorized to read package'))
        except logic.NotFound:
            abort(404, _('Dataset not found'))

    def delete_dataset_from_basket(self, id):
        """
        Remove the given dataset from the basket.
        """
        
        context = {
            'model': model, 'session': model.Session,
            'user': c.user or c.author, 'for_view': True
        }

        data_dict = {'id': id}

        # Check the package exists
        try:
            pkg_dict = logic.get_action('package_show')(context, data_dict)
        except logic.NotAuthorized:
            abort(401, _('Unauthorized to read package'))
        except logic.NotFound:
            abort(404, _('Dataset not found'))

        self._remove_from_basket(pkg_dict['id'])
        redirect(self._basket_contents_url)

    # --- Helper methods --- #

    def _add_to_basket(self, id):
        _basket.add(id, category='dataset')

    @property
    def _basket_contents(self):
        return basket_contents()

    @property
    def _basket_contents_url(self):
        return h.url_for(controller='ckanext.dgu.controllers.basket:BasketController',
                         action='contents')

    def _remove_from_basket(self, id):
        _basket.remove(id, category='dataset')

