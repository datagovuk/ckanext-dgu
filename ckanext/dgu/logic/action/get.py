from ckan.logic import get_or_bust
from ckan.logic import NotFound, check_access
from ckan.logic import side_effect_free
import ckan.lib.dictization.model_dictize as model_dictize
from ckan import plugins
import ckan.lib.plugins as lib_plugins
from ckan.lib.navl.dictization_functions import validate
from ckan.logic.action.get import organization_show
from ckanext.dgu.model.schema_codelist import Schema, Codelist

#from ckan.plugins.toolkit as t

log = __import__('logging').getLogger(__name__)

@side_effect_free
def publisher_show(context, data_dict):
    '''Shows publisher details.
    Based on group_show, but has parent group, as well as the child groups.

    May raise NotFound or NotAuthorized.
    '''
    group_dict = organization_show(context, data_dict)

    model = context['model']
    id = get_or_bust(data_dict, 'id')
    group = model.Group.get(id)

    parent_groups = group.get_parent_groups(type='organization')
    group_dict['parent_group'] = {'id': parent_groups[0].id, 'name': parent_groups[0].name} \
                                 if parent_groups else None

    return group_dict

@side_effect_free
def suggest_themes(context, data_dict):
    '''Suggests themes for a dataset or the component parts of a dataset

    To be able to determine the primary and secondary theme, the description
    tags and title are required for a Package. The categorize_package function
    requires works with Package models and a dictionary, so both versions are
    supported.  If an id is passed, then the package will be retrieved and passed
    to the categorisation, otherwise it will be formatted as per the required
    dictionary.
    '''
    from ckanext.dgu.lib.theme import categorize_package2
    themes = []

    # TODO: Make this only available to logged in publishers

    model = context['model']

    id = data_dict.get('id')
    if id:
        pkg = model.Package.get(id)
        themes = categorize_package2(pkg)
    else:
        pkg_dict = {'name': data_dict.get('name'),
                    'title': data_dict.get('title'),
                    'notes': data_dict.get('notes'),
                    'tags': [t for t in data_dict.get('tags', '').split(',')],
                    'extras': [{'key': '', 'value': ''}]
                    }
        themes = categorize_package2(pkg_dict)

    results = {'primary-theme': {}, 'secondary-theme': []}
    if len(themes) >= 1:
        results['primary-theme'] = themes[0]

    results['secondary-theme'] = themes[1:]

    return results

def schema_list(context, data_dict):
    check_access('schema_list', context, data_dict) 

    model = context['model']
    items = model.Session.query(Schema).order_by('title')
    return [item.as_dict() for item in items.all()]

@side_effect_free
def codelist_list(context, data_dict):
    check_access('codelist_list', context, data_dict) 

    model = context['model']
    items = model.Session.query(Codelist).order_by('title')
    return [item.as_dict() for item in items.all()]
