

def collection_create(context=None, data_dict=None):
    """
    Does the user have permission to create a collection?
    Only publishers and sysadmins do so permission is
    granted if the user is a member of at least one group.
    If the user is a sysadmin, this call won't be made as it is
    unnecessary.
    """
    from ckan.logic.auth.create import group_create

    model = context.get('model')
    user = context.get('auth_user_obj')
    if not user:
        return {'success': False}

    if context.get('type') != 'collection':
        return group_create (context, data_dict)

    gids = user.get_group_ids(group_type='organization')
    return {'success': bool(len(gids) > 0)}
