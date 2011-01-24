class ScriptError(Exception):
    pass

def remove_readonly_fields(pkg):
    '''Takes a package dictionary and gets rid of any read-only fields
    so that you can write the package to the API.'''
    for read_only_field in ('id', 'relationships', 'ratings_average',
                            'ratings_count', 'ckan_url',
                            'metadata_modified',
                            'metadata_created'):
        if pkg.has_key(read_only_field):
            del pkg[read_only_field]
