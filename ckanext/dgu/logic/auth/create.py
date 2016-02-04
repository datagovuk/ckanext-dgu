

def collection_create(context=None, data_dict=None):
    """
    Does the user have permission to create a collection?
    Only publishers and sysadmins do so permission is
    granted if the user is a member of at least one group.
    If the user is a sysadmin, this call won't be made as it is
    unnecessary.
    """
    from ckan.logic.auth.create import group_create

    print "COLLECTION_CREATE"

    model = context.get('model')
    user = context.get('auth_user_obj')
    if not user:
        return {'success': False}

    type = context.get('type') or (data_dict and data_dict.get('type'))

    if type != 'collection':
        return group_create (context, data_dict)

    gids = user.get_group_ids(group_type='organization')
    print gids
    return {'success': bool(len(gids) > 0)}
