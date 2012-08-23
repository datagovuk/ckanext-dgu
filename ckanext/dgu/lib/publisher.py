from ckan import model
from ckan.model.group import HIERARCHY_CTE

def go_up_tree(publisher):
    '''Provided with a publisher object, it walks up the hierarchy and yields each publisher,
    including the one you supply.'''
    yield publisher
    for parent in get_parents(publisher):
        for grandparent in go_up_tree(parent):
            yield grandparent

def go_down_tree(publisher):
    '''Provided with a publisher object, it walks down the hierarchy and yields each publisher,
    including the one you supply.'''
    yield publisher
    for child in get_children(publisher):
        for grandchild in go_down_tree(child):
            yield grandchild

def get_parents(publisher):
    '''Finds parent publishers for the given publisher (object). (Not recursive)'''
    return publisher.get_groups('publisher')

def get_children(publisher):
    '''Finds child publishers for the given publisher (object). (Not recursive)'''
    return model.Session.query(model.Group).\
           from_statement(HIERARCHY_CTE).params(id=publisher.id, type='publisher').\
           all()

def get_top_level():
    '''Returns the top level publishers.'''
    return model.Session.query(model.Group).\
           outerjoin(model.Member, model.Member.table_id == model.Group.id and \
                     model.Member.table_name == 'group' and \
                     model.Member.state == 'active').\
           filter(model.Member.id==None).\
           filter(model.Group.type=='publisher').\
           order_by(model.Group.name).all()
