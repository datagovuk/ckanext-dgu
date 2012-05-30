from logging import getLogger
import re

from ckan.model.group import Group
from ckanext.dgu.lib.resource_formats import ResourceFormats

log = getLogger(__name__)

class SearchIndexing(object):
    '''Functions that edit the package dictionary fields to affect the way it
    gets indexed in Solr.'''
    
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
    def resource_format_cleanup(cls, pkg_dict):
        '''Standardises the res_format field.'''
        pkg_dict['res_format'] = [ cls._clean_format(f) for f in pkg_dict.get('res_format', []) ]
        
    _disallowed_characters = re.compile(r'[^a-zA-Z]')
    @classmethod
    def _clean_format(cls, format_string):
        if isinstance(format_string, basestring):
            matched_format = ResourceFormats.match(format_string)
            if matched_format:
                return matched_format
            return re.sub(cls._disallowed_characters, '', format_string)
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
    def add_field__publisher(cls, pkg_dict):
        '''Adds the 'publisher' based on group.'''
        groups = set([Group.get(g) for g in pkg_dict['groups']])
        publishers = [g for g in groups if g.type == 'publisher']

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
        
