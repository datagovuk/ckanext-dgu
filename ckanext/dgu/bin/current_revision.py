'''Tool for fixing problems to do with a resource without a 'current'
resource_revision'''

from optparse import OptionParser
import logging
import datetime

import common
from running_stats import StatsList

# NB put no CKAN imports here, or logging breaks


def _get_resources(state, options):
    resources = model.Session.query(model.Resource) \
                .filter_by(state=state) \
                .join(model.ResourceGroup) \
                .join(model.Package) \
                .filter_by(state='active')
    if options.dataset:
        resources = resources.filter(model.Package.name==options.dataset)
    if options.resource:
        resources = resources.filter(model.Resource.id==options.resource)
    resources = resources.all()
    print '%i resources' % len(resources)
    return resources


def no_current(options):
    resources = _get_resources('active', options)
    stats = StatsList()
    need_to_commit = False
    for res in resources:
        latest_res_rev = model.Session.query(model.ResourceRevision).filter_by(id=res.id).order_by(model.ResourceRevision.revision_timestamp.desc()).first()
        if not latest_res_rev.current:
            print add_stat('No current revision', res, stats)
            if options.write:
                latest_res_rev.current = True
                need_to_commit = True
        else:
            add_stat('Ok', res, stats)
        if latest_res_rev.revision_id != res.revision_id:
            print add_stat('Revision ID of resource too old', res, stats)
            if options.write:
                res.revision_id = latest_res_rev.revision_id
                need_to_commit = True

    print 'Summary', stats.report()
    if options.write and need_to_commit:
        model.repo.commit_and_remove()
        print 'Written'


def undelete(options):
    resources = _get_resources('deleted', options)
    stats = StatsList()
    if options.write:
        rev = model.repo.new_revision()
        rev.author = 'current_revision_fixer2'
    need_to_commit = False
    for res in resources:
        # when viewing old revision of the dataset, there is one where the
        # resources are not deleted but they don't show up. This is seen where resource_revision has an expired_timestamp that has no corresponding revision_timestamp - i.e. a gap between them (and that is not 9999-12-31).
        # e.g. select revision_timestamp,expired_timestamp,current from resource_revision where id='373bb814-7a49-4f53-8a0e-762002b2529c' order by revision_timestamp;
        #      revision_timestamp     |     expired_timestamp      | current
        # ----------------------------+----------------------------+---------
        # 2013-06-19 00:50:28.880058 | 2014-01-18 01:03:47.500041 | f
        # 2014-01-18 01:03:47.500041 | 2014-01-18 01:03:48.296204 | f
        # 2014-01-18 01:03:50.612196 | 9999-12-31 00:00:00        | t
        # Clearly there is a gap from the 2nd to the 3rd, indicating the problem.
        res_revs = model.Session.query(model.ResourceRevision).filter_by(id=res.id).order_by('revision_timestamp').all()
        if len(res_revs) < 2:
            print add_stat('Not enought revisions', res, stats)
            continue
        if res_revs[-2].expired_timestamp == res_revs[-1].revision_timestamp:
            add_stat('Ok', res, stats)
            continue
        print add_stat('Timestamp gap', res, stats)
        if options.write:
            res.state = 'active'
            need_to_commit = True
    print 'Summary', stats.report()
    if options.write and need_to_commit:
        model.repo.commit_and_remove()
        print 'Written'

END_OF_TIME = datetime.datetime(9999, 12, 31)
def refix(options):
    resources = _get_resources('active', options)
    stats = StatsList()
    need_to_commit = False
    for res in resources:
        # the old uncommit command would set the wrong resource_revision to be current.
        # e.g. select revision_timestamp,expired_timestamp,current from resource_revision where id='b2972b35-b6ae-4096-b8cc-40dab3927a71' order by revision_timestamp;
        #     revision_timestamp     |     expired_timestamp      | current
        # ---------------------------+----------------------------+---------i
        # 2013-04-13 01:47:30.18897  | 2013-06-18 19:01:45.910899 | f
        # 2013-06-18 19:01:45.910899 | 2014-01-18 08:55:41.443349 | t
        # 2014-01-18 08:55:41.443349 | 2014-01-18 08:55:41.566383 | f
        # Clearly only the latest should be current.
        res_revs = model.Session.query(model.ResourceRevision).filter_by(id=res.id).order_by('revision_timestamp').all()
        fix_needed = False
        if len(res_revs) < 2:
            print add_stat('Not enought revisions', res, stats)
            continue
        for res_rev in res_revs[:-1]:
            if res_rev.current:
                print add_stat('Early revision is current', res, stats)
                fix_needed = True
                if options.write:
                    res_rev.current = False
                    need_to_commit = True
        if not res_revs[-1].current:
            print add_stat('Last revision is not current', res, stats)
            fix_needed = True
            if options.write:
                res_revs[-1].current = True
                need_to_commit = True
        if res_revs[-1].expired_timestamp != END_OF_TIME:
            print add_stat('Last revision is not 9999', res, stats)
            fix_needed = True
            if options.write:
                res_revs[-1].expired_timestamp = END_OF_TIME
                need_to_commit = True
        if not fix_needed:
            add_stat('Ok', res, stats)
            continue
    print 'Summary', stats.report()
    if options.write and need_to_commit:
        model.repo.commit_and_remove()
        print 'Written'

def add_stat(outcome, res, stats):
    return stats.add(outcome, '%s %s' % (res.resource_group.package.name, res.id[:4]))


if __name__ == '__main__':
    usage = """Tool for fixing problems to do with resources that have no
    'current' resource_revision

    usage: %prog [options] <ckan.ini> <command>
Commands:
    no-current - Fix resources without a current revision
    undelete - Undelete resources that were deleted because of the problem
    refix - Sort out resources that were falsely made current in a bad fix
    """
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-r', '--resource', dest='resource')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments (%i)' % len(args))
    config_ini, command = args
    commands = ('no-current', 'undelete', 'refix')
    if command not in commands:
        parser.error('Command %s should be one of: %s' % (command, commands))
    print 'Loading CKAN config...'
    common.load_config(config_ini)
    common.register_translator()
    print 'Done'
    # Setup logging to print debug out for theme stuff only
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.WARNING)
    localLogger = logging.getLogger(__name__)
    localLogger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    localLogger.addHandler(handler)
    #logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    from ckan import model
    if command == 'no-current':
        no_current(options)
    elif command == 'undelete':
        undelete(options)
    elif command == 'refix':
        refix(options)
    else:
        raise NotImplemented()
