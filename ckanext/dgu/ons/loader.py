import re

from ckanext.loader import ResourceSeriesLoader

class OnsLoader(ResourceSeriesLoader):
    def __init__(self, ckanclient):
        field_keys_to_find_pkg_by = ['title', 'department']
        resource_id_prefix = 'hub/id/'
        self.resource_id_matcher = re.compile('.* \| hub\/id\/([0-9\-]*)')
        field_keys_to_expect_invariant = [
            'update_frequency', 'geographical_granularity',
            'geographic_coverage', 'temporal_granularity',
            'precision', 'url', 'taxonomy_url', 'agency',
            'author', 'author_email', 'license_id']
        synonyms = {'department': [
            ('Department for Education',
             'Department for Children, Schools and Families'),
            ]}
        super(OnsLoader, self).__init__(
            ckanclient,
            field_keys_to_find_pkg_by,
            resource_id_prefix,
            field_keys_to_expect_invariant=field_keys_to_expect_invariant,
            synonyms=synonyms
            )

    def _get_search_options(self, field_keys, pkg_dict):
        if pkg_dict['extras']['department']:
            search_options_list = super(OnsLoader, self)._get_search_options(field_keys, pkg_dict)
        else:
            # if department is blank then search against agency instead
            # (department may have been filled in manually)
            field_keys.append('agency')
            field_keys.remove('department')
            search_options_list = super(OnsLoader, self)._get_search_options(field_keys, pkg_dict)
        return search_options_list

    def _get_hub_id(self, resource):
        '''For a given resource, returns its hub id
        e.g. "April 2009 data: Experimental Statistics | hub/id/119-46440"
              gives "119-46440"
        '''
        id_match = self.resource_id_matcher.match(resource['description'])
        if not id_match:
            return None
        return id_match.groups()[0]

    def _merge_resources(self, existing_pkg, pkg):
        merged_dict = super(OnsLoader, self)._merge_resources(existing_pkg, pkg)
        # sort resources by hub_id
        cmp_hub_id = lambda res1, res2: cmp(self._get_hub_id(res1),
                                                self._get_hub_id(res2))
        merged_dict['resources'] = sorted(merged_dict['resources'], cmp=cmp_hub_id)
        return merged_dict
