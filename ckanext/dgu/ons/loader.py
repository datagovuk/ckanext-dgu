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

