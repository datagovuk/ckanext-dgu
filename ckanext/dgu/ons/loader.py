from ckanext.loader import ResourceSeriesLoader

class OnsLoader(ResourceSeriesLoader):
    def __init__(self, ckanclient):
        field_keys_to_find_pkg_by = ['title', 'department']
        resource_id_prefix = 'hub/id/'
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
