


def group_members_of_type(group_id, member_type, capacity=None ):
    from ckan import model

    object_type_string = member_type.__name__.lower()
    query = model.Session.query(member_type).\
           filter(model.Group.id == group_id).\
           filter(model.Member.state == 'active').\
           filter(model.Member.table_name == object_type_string)

    if hasattr(member_type,'state'):
        query = query.filter(member_type.state == 'active' )

    if capacity:
        query = query.filter(model.Member.capacity == capacity)

    query = query.join(model.Member, model.Member.table_id == getattr(member_type,'id') ).\
           join(model.Group, model.Group.id == model.Member.group_id)
    return query