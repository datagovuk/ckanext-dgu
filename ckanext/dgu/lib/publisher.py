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

def openness_scores(publisher, include_sub_publishers=False):
    """
        For the provided publisher, this grabs the resource ids
        and finds the matching openness scores in the task_status
        table to return a total number of entries (which should be
        the same as the resource count) and dictionary containing
        a count for each score such as {0:3, 1:0, 2:1 ...}
    """
    from collections import defaultdict

    q = """SELECT TS.value::INT from task_status  as TS
           WHERE TS.task_type='qa' AND
                 TS.entity_type ='resource' AND
                 TS.key = 'openness_score' AND
                 TS.entity_id in (
                   SELECT R.id from resource  as R
                   INNER JOIN resource_group as RG ON RG.id = R.resource_group_id
                   INNER JOIN package as P ON P.id = RG.package_id
                   WHERE P.state = 'active' AND R.state='active' AND
                         P.id in (SELECT table_id FROM member
                                  WHERE group_id in ({pub_id})
                                  AND table_name='package' AND state='active')
                                 );"""

    d = defaultdict(int)

    if include_sub_publishers:
        pubids = ["'%s'" % p.id for p in go_down_tree(publisher)]
    else:
        pubids = ["'%s'" % publisher.id]

    for m in model.Session.execute(q.format(pub_id=','.join(pubids))):
        d[m[0]] += 1
    total = sum(d.values())

    return total, d

def resource_count(publisher, include_sub_publishers=False):
    """
        Counts the number of active resources within active datasets and
        returns the scalar.
    """
    q = """SELECT count(R.id) from resource  as R
           INNER JOIN resource_group as RG ON RG.id = R.resource_group_id
           INNER JOIN package as P ON P.id = RG.package_id
           WHERE P.state = 'active' AND R.state='active' AND
                 P.id in (SELECT table_id FROM member
                          WHERE group_id IN ({pub_id})
                          AND table_name='package' AND state='active');"""

    if include_sub_publishers:
        pubids = ["'%s'" % p.id for p in go_down_tree(publisher)]
    else:
        pubids = ["'%s'" % publisher.id]

    return model.Session.scalar(q.format(pub_id=','.join(pubids)))

