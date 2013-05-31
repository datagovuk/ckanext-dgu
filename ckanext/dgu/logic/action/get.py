from ckan.logic import get_or_bust
from ckan.logic import NotFound, check_access
from ckan.logic import side_effect_free
import ckan.lib.dictization.model_dictize as model_dictize
from ckan import plugins
import ckan.lib.plugins as lib_plugins
from ckan.lib.navl.dictization_functions import validate
from ckan.logic.action.get import group_show
from ckanext.dgu.lib import publisher as publisher_lib

#from ckan.plugins.toolkit as t

log = __import__('logging').getLogger(__name__)

@side_effect_free
def publisher_show(context, data_dict):
    '''Shows publisher details.
    Based on group_show, but has parent group, as well as the child groups.

    May raise NotFound or NotAuthorized.
    '''
    group_dict = group_show(context, data_dict)

    model = context['model']
    id = get_or_bust(data_dict, 'id')
    group = model.Group.get(id)

    parent_groups = publisher_lib.get_parents(group)
    group_dict['parent_group'] = parent_groups[0].name if parent_groups else None

    return group_dict
