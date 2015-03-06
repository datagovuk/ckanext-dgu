from ckan.logic import auth_allow_anonymous_access

@auth_allow_anonymous_access
def schema_list(context=None, data_dict=None):
    """
    Does the user have permission to list the schema available.
    This is always yes.
    """
    return {'success': True}

@auth_allow_anonymous_access
def codelist_list(context=None, data_dict=None):
    """
    Does the user have permission to list the codelist available.
    This is always yes.
    """
    return {'success': True}
