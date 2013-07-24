from logging import getLogger
import re
import string

from ckan.model.group import Group
from ckan import model
from ckanext.dgu.lib.formats import Formats
from ckanext.dgu.plugins_toolkit import ObjectNotFound

log = getLogger(__name__)

class SearchIndexing(object):
    '''Functions that edit the package dictionary fields to affect the way it
    gets indexed in Solr.'''

    @classmethod
    def add_popularity(cls, pkg_dict):
        '''Adds the views field from the ga-report plugin, if it is installed'''
        from pylons import config

        score = 0
        if 'ga-report' in config.get('ckan.plugins'):
            from ckanext.ga_report.ga_model import get_score_for_dataset
            score = get_score_for_dataset(pkg_dict['name'])

        pkg_dict['popularity'] = score

    @classmethod
    def add_inventory(cls, pkg_dict):
        ''' Sets inventory to false if not present '''
        pkg_dict['inventory'] = pkg_dict.get('inventory', False)
        log.debug('Inventory? %s: %s', pkg_dict['inventory'], pkg_dict['name'])


    @classmethod
    def add_field__is_ogl(cls, pkg_dict):
        '''Adds the license_id-is-ogl field.'''
        if not pkg_dict.has_key('license_id-is-ogl'):
            is_ogl = cls._is_ogl(pkg_dict)
            pkg_dict['license_id-is-ogl'] = is_ogl
            pkg_dict['extras_license_id-is-ogl'] = is_ogl

    @classmethod
    def _is_ogl(cls, pkg_dict):
        """
        Returns true iff the represented dataset has an OGL license

        A dataset has an OGL license if the license_id == "uk-ogl"
        or if it's a UKLP dataset with "Open Government License" in the
        access_contraints extra field.
        """
        regex = re.compile(r'open government licen[sc]e', re.IGNORECASE)
        return pkg_dict['license_id'] == 'uk-ogl' or \
               bool(regex.search(pkg_dict.get('extras_access_constraints', '')))

    @classmethod
    def clean_title_string(cls, pkg_dict):
        ''' Removes leading spaces from the title_string that is used for searching '''
        ts = pkg_dict.get('title_string', '').lstrip()  # strip leading whitespace
        if ts and ts[0] in string.punctuation:
            # Remove leading punctuation where we find it.
            ts = ts.replace(ts[0], '')
        pkg_dict['title_string'] = ts


    @classmethod
    def resource_format_cleanup(cls, pkg_dict):
        '''Standardises the res_format field.'''
        pkg_dict['res_format'] = [ cls._clean_format(f) for f in pkg_dict.get('res_format', []) ]

    _disallowed_characters = re.compile(r'[^a-zA-Z /+]')
    @classmethod
    def _clean_format(cls, format_string):
        if isinstance(format_string, basestring):
            matched_format = Formats.match(format_string)
            if matched_format:
                return matched_format['display_name']
            return re.sub(cls._disallowed_characters, '', format_string).strip()
        else:
            return format_string

    @classmethod
    def add_field__group_titles(cls, pkg_dict):
        '''Adds the group titles.'''
        groups = [Group.get(g) for g in pkg_dict['groups']]

        # Group titles
        if not pkg_dict.has_key('group_titles'):
            pkg_dict['group_titles'] = [g.title for g in groups]
        else:
            log.warning('Unable to add "group_titles" to index, as the datadict '
                        'already contains a key of that name')

    @classmethod
    def add_field__group_abbreviation(cls, pkg_dict):
        '''Adds any group abbreviation '''
        abbr = None
        for g in [Group.get(g) for g in pkg_dict['groups']]:
            abbr = g.extras.get('abbreviation')
            break

        if abbr:
            pkg_dict['group_abbreviation'] = abbr
            log.debug('Abbreviations %s: %s', pkg_dict['name'], abbr)

    @classmethod
    def add_field__publisher(cls, pkg_dict):
        '''Adds the 'publisher' based on group.'''
        import ckan.model as model

        # pkg_dict['groups'] here is returning groups found by a relationship
        # or membership that has been deleted, but not had the revision set
        # to non-current
        #groups = set([Group.get(g) for g in pkg_dict['groups']])
        #publishers = [g for g in groups if g.type == 'publisher']
        publishers = model.Package.get(pkg_dict['id']).get_groups('publisher')

        # Each dataset should have exactly one group of type "publisher".
        # However, this is not enforced in the data model.
        if len(publishers) > 1:
            log.warning('Dataset %s seems to have more than one publisher!  '
                        'Only indexing the first one: %s', \
                        pkg_dict['name'], repr(publishers))
            publishers = publishers[:1]
        elif len(publishers) == 0:
            log.warning('Dataset %s doesn\'t seem to have a publisher!  '
                        'Unable to add publisher to index.',
                        pkg_dict['name'])
            return pkg_dict

        # Publisher names
        if not pkg_dict.has_key('publisher'):
            pkg_dict['publisher'] = [p.name for p in publishers]
        else:
            log.warning('Unable to add "publisher" to index, as the datadict '
                        'already contains a key of that name')

        # Ancestry of publishers
        ancestors = []
        publisher = publishers[0]
        while(publisher is not None):
            ancestors.append(publisher)
            parent_publishers = publisher.get_groups('publisher')
            if len(parent_publishers) == 0:
                publisher = None
            else:
                if len(parent_publishers) > 1:
                    log.warning('Publisher %s has more than one parent publisher. '
                                'Ignoring all but the first. %s',
                                publisher, repr(parent_publishers))
                publisher = parent_publishers[0]


        if not pkg_dict.has_key('parent_publishers'):
            pkg_dict['parent_publishers'] = [ p.name for p in ancestors ]
        else:
            log.warning('Unable to add "parent_publishers" to index, as the datadict '
                        'already contains a key of that name. '
                        'Package: %s Parent_publishers: %r', \
                        pkg_dict['name'], pkg_dict['parent_publishers'])

    @classmethod
    def add_field__harvest_document(cls, pkg_dict):
        '''Index a harvested dataset\'s XML content
           (Given a low priority when searching)'''
        if pkg_dict.get('UKLP', '') == 'True':
            import ckan
            from ckanext.dgu.plugins_toolkit import get_action

            context = {'model': ckan.model,
                       'session': ckan.model.Session,
                       'ignore_auth': True}

            data_dict = {'id': pkg_dict.get('harvest_object_id', '')}

            try:
                harvest_object = get_action('harvest_object_show')(context, data_dict)
                pkg_dict['extras_harvest_document_content'] = harvest_object.get('content', '')
            except ObjectNotFound:
                log.warning('Unable to find harvest object "%s" '
                            'referenced by dataset "%s"',
                            data_dict['id'], pkg_dict['id'])

    @classmethod
    def add_field__openness(cls, pkg_dict):
        '''Add the openness score (stars) to the search index'''
        pkg = model.Session.query(model.Package).get(pkg_dict['id'])
        pkg_score = None
        for res in pkg.resources:
            status = model.Session.query(model.TaskStatus).\
                     filter_by(entity_id=res.id).\
                     filter_by(task_type='qa').\
                     filter_by(key='status').first()
            if status:
                score = status.value
                if not pkg_score or score > pkg_score:
                    pkg_score = score
        if not pkg.resources:
            pkg_score = 0
        if pkg_score is None:
            pkg_score = -1
        pkg_dict['openness_score'] = pkg_score
        log.debug('Openness score %s: %s', pkg_score, pkg_dict['name'])
