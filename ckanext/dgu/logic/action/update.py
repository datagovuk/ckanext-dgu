


def add_to_collection(context, data_dict):
    data_dict = {"id": new_group,
                 "object": id,
                 "object_type": 'package',
                 "capacity": 'public'}
    try:
        get_action('member_create')(context, data_dict)
    except NotFound:
        abort(404, _('Group not found'))

def remove_from_collection(context, data_dict):
    data_dict = {"id": new_group,
                 "object": id,
                 "object_type": 'package',
                 "capacity": 'public'}
    try:
        get_action('member_create')(context, data_dict)
    except NotFound:
        abort(404, _('Group not found'))
