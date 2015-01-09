from ckan import model
import logging

log = logging.getLogger(__name__)

def go_up_tree(publisher):
    '''Provided with a publisher object, it walks up the hierarchy and yields
    each publisher, including the one you supply.

    Essentially this is a slower version of Group.get_parent_group_hierarchy
    because it returns Group objects, rather than dicts. And it includes the
    publisher you supply.
    '''
    yield publisher
    for parent in publisher.get_parent_groups(type='organization'):
        for grandparent in go_up_tree(parent):
            yield grandparent

def go_down_tree(publisher):
    '''Provided with a publisher object, it walks down the hierarchy and yields
    each publisher, including the one you supply.
   
    Essentially this is a slower version of Group.get_children_group_hierarchy
    because it returns Group objects, rather than dicts.
    '''
    yield publisher
    for child in publisher.get_children_groups(type='organization'):
        for grandchild in go_down_tree(child):
            yield grandchild

def find_group_admins(group):
    '''Look for publisher admins up the tree'''
    recipients = []
    recipient_publisher = None
    for publisher in go_up_tree(group):
        admins = publisher.members_of_type(model.User, 'admin').all()
        if admins:
            recipients = [(u.fullname,u.email) for u in admins]
            recipient_publisher = publisher.title
            break

    return recipients, recipient_publisher

def cached_openness_scores(reports_to_run=None):
    """
    This function is called by the ICachedReport plugin which will
    iterate over all of the publishers and generate an openness score
    for them on a regular basis
    """
    import json
    from ckan.lib.json import DateTimeJsonEncoder

    local_reports = set(['openness-scores', 'openness-scores-withsub'])
    if reports_to_run:
      local_reports = set(reports_to_run) & local_reports

    if not local_reports:
      return

    publishers = model.Session.query(model.Group).\
        filter(model.Group.type=='publisher').\
        filter(model.Group.state=='active')

    log.info("Generating openness-scores report")
    log.info("Fetching %d publishers" % publishers.count())

    for publisher in publishers.all():
        # Run the openness report with and without include_sub_organisations set
        if 'openness-scores' in local_reports:
          log.info("Generating openness scores for %s" % publisher.name)
          val = openness_scores(publisher, use_cache=False)
          model.DataCache.set(publisher.name, "openness-scores", json.dumps(val,cls=DateTimeJsonEncoder))

        if 'openness-scores-withsub' in local_reports:
          val = openness_scores(publisher, include_sub_publishers=True, use_cache=False)
          model.DataCache.set(publisher.name, "openness-scores-withsub", json.dumps(val,cls=DateTimeJsonEncoder))

    model.Session.commit()

def openness_scores(publisher, include_sub_publishers=False, use_cache=True):
    """
        For the provided publisher, this grabs the resource ids
        and finds the matching openness scores in the task_status
        table to return a total number of entries (which should be
        the same as the resource count) and dictionary containing
        a count for each score such as {0:3, 1:0, 2:1 ...}
    """
    from collections import defaultdict

    if use_cache:
        key = 'openness-scores'
        if include_sub_publishers:
            key = "".join([key, '-withsub'])
        cache = model.DataCache.get_fresh(publisher.name, key)
        if cache:
            log.info("Found openness score in cache: %s" % cache)
            return cache


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
        d[str(m[0])] += 1
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

