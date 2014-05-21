from logging import getLogger
import re
import string

from paste.deploy.converters import asbool

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

        try:
            if asbool(pkg_dict.get('unpublished', False)):
                from ckanext.dgu.lib.helpers import feedback_comment_count
                score += feedback_comment_count(pkg_dict)
                log.debug('Updated score for unpublished item {0} to {1}'.format(pkg_dict['name'], score))
        except ValueError:
            # If the unpublished field is not a proper bool then we should assume it is false
            pass

        if 'ga-report' in config.get('ckan.plugins'):
            from ckanext.ga_report.ga_model import get_score_for_dataset
            score += get_score_for_dataset(pkg_dict['name'])

        pkg_dict['popularity'] = score
        log.info("Popularity for {0} is {1}".format(pkg_dict['name'], pkg_dict['popularity']))

    @classmethod
    def add_inventory(cls, pkg_dict):
        ''' Sets unpublished to false if not present and also states whether the item is marked
            as never being published. '''
        pkg_dict['unpublished'] = pkg_dict.get('unpublished', False)
        log.debug('Unpublished? %s: %s', pkg_dict['unpublished'], pkg_dict['name'])

        pkg_dict['core_dataset'] = pkg_dict.get('core-dataset', False)
        log.debug('NII dataset? %s: %s', pkg_dict['core_dataset'], pkg_dict['name'])

        # We also need to mark whether it is restricted (as in it will never be
        # released).
        pkg_dict['publish_restricted'] = pkg_dict.get('publish-restricted', False)
        log.debug('Will not be published? %s: %s', pkg_dict['publish_restricted'], pkg_dict['name'])


    @classmethod
    def add_field__is_ogl(cls, pkg_dict):
        '''Adds the license_id-is-ogl field.'''
        if 'license_id-is-ogl' not in pkg_dict:
            is_ogl = cls._is_ogl(pkg_dict)
            pkg_dict['license_id-is-ogl'] = is_ogl
            pkg_dict['extras_license_id-is-ogl'] = is_ogl
        try:
            if asbool(pkg_dict.get('unpublished', False)):
                pkg_dict['license_id-is-ogl'] = 'unpublished'
        except ValueError:
            pass

    @classmethod
    def _is_ogl(cls, pkg_dict):
        """
        Returns true iff the represented dataset has an OGL license

        A dataset has an OGL license if the license_id == "uk-ogl"
        or if it's a UKLP dataset with "Open Government License" in the
        'licence_url_title' or 'licence' extra fields
        """
        regex = re.compile(r'open government licen[sc]e', re.IGNORECASE)
        return pkg_dict['license_id'] == 'uk-ogl' or \
               bool(regex.search(pkg_dict.get('extras_licence_url_title', ''))) or \
               bool(regex.search(pkg_dict.get('extras_licence', '')))

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
        if not pkg_dict.has_key('organization_titles'):
            pkg_dict['organization_titles'] = [g.title for g in groups]
        else:
            log.warning('Unable to add "organization_titles" to index, as the datadict '
                        'already contains a key of that name')

    @classmethod
    def add_field__group_abbreviation(cls, pkg_dict):
        '''Adds any group abbreviation '''
        abbr = None

        g = model.Group.get(pkg_dict['organization'])
        if not g:
            log.error("Package %s does not belong to an organization" % pkg_dict['name'])
            return

        try:
            abbr = g.extras.get('abbreviation')
        except:
            raise

        if abbr:
            pkg_dict['group_abbreviation'] = abbr
            log.debug('Abbreviations %s: %s', pkg_dict['name'], abbr)

    @classmethod
    def add_field__publisher(cls, pkg_dict):
        '''Adds the 'publisher' based on group.'''
        import ckan.model as model

        publisher = model.Group.get(pkg_dict.get('organization'))
        if not publisher:
            log.warning('Dataset %s doesn\'t seem to have a publisher!  '
                        'Unable to add publisher to index.',
                        pkg_dict['name'])
            return pkg_dict

        # Publisher names
        if not pkg_dict.has_key('publisher'):
            pkg_dict['publisher'] = publisher.name
            log.info(u"{0} is the publisher for {1}".format(publisher.name, pkg_dict['name']))
        else:
            log.warning('Unable to add "publisher" to index, as the datadict '
                        'already contains a key of that name')

        # Ancestry of publishers
        ancestors = []
        while(publisher is not None):
            ancestors.append(publisher)
            parent_publishers = publisher.get_parent_groups('organization')
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
        import ckan
        from ckanext.dgu.plugins_toolkit import get_action
        context = {'model': ckan.model, 'session': ckan.model.Session,
                   'ignore_auth': True}
        data_dict = {'id': pkg_dict['id']}
        try:
            qa_openness = get_action('qa_package_openness_show')(context, data_dict)
        except ObjectNotFound:
            log.warning('No QA info for package %s', pkg_dict['name'])
            return
        except KeyError:
            # occurs during tests or if you've not install ckanext-qa
            log.warning('QA not installed - not indexing it.')
            return
        pkg_dict['openness_score'] = qa_openness.get('openness_score')
        log.debug('Openness score %s: %s', pkg_dict['openness_score'], pkg_dict['name'])

        try:
            qa_broken = get_action('qa_package_broken_show')(context, data_dict)
        except ObjectNotFound:
            log.warning('No brokenness info for package %s', pkg_dict['name'])
            return
        if not hasattr(cls, 'broken_links_map'):
            cls.broken_links_map = {
                    True: 'Broken',
                    'some': 'Partially broken',
                    False: 'OK',
                    None: 'TBC'
                    }
        pkg_dict['broken_links'] = cls.broken_links_map[qa_broken.get('archival_is_broken')]
        log.debug('Broken links %s: %s', pkg_dict['broken_links'], pkg_dict['name'])

