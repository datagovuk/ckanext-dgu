'''Tool for removing revisions (#1375) inadvertantly changing the resource URL and adding
WMS/WFS parameters several times.'''

from optparse import OptionParser
import logging
import datetime

import common
from running_stats import StatsList

# pip install 'ProgressBar==2.3'
from progressbar import ProgressBar, Percentage, Bar, ETA, Counter

# NB put no CKAN imports here, or logging breaks

END_OF_TIME = datetime.datetime(9999, 12, 31)

def wms_revisions(options):
    '''
    These revisions look like this:

    # select url from resource_revision where id='3b157e17-cef2-43dc-b0ce-76de18549852' order by revision_timestamp;
    http://www.acas.org.uk/CHttpHandler.ashx?id=2918&p=0
    http://www.acas.org.uk/CHttpHandler.ashx?id=2918&p=0
    http://www.acas.org.uk/CHttpHandler.ashx?id=2918&p=0
    http://www.acas.org.uk/CHttpHandler.ashx?service=WMS&request=GetCapabilities&version=1.3
    http://www.acas.org.uk/CHttpHandler.ashx?service=WMS&request=GetCapabilities&version=1.1.1
    http://www.acas.org.uk/CHttpHandler.ashx?service=WFS&request=GetCapabilities&version=2.0
    http://www.acas.org.uk/CHttpHandler.ashx?service=WMS&request=GetCapabilities&version=1.3

    The bad ones have been changed to "?service=" params. These revisions need removing.

    # Typical revision:
                     id                  |         timestamp          |           author           |                         message                          | state  | approved_timestamp
    a2370bd1-b1b8-41b4-9fc1-d38b46d2fbda | 2014-02-22 04:34:56.634442 | co-prod3.dh.bytemark.co.uk | REST API: Update object financial-transactions-data-acas | active |
    # i.e. author='co-prod3...' (site-user, via API)
    '''
    resources = common.get_resources(state='active',
            resource_id=options.resource, dataset_name=options.dataset)
    stats = StatsList()
    stats.report_value_limit = 1000
    total_bad_revisions = 0
    need_to_commit = False
    widgets = ['Resources: ', Percentage(), ' ', Bar(), ' ', ETA()]
    progress = ProgressBar(widgets=widgets)
    for res in progress(resources):
        res = model.Resource.get(res.id)  # as the session gets flushed during the loop
        res_rev_q = model.Session.query(model.ResourceRevision).filter_by(id=res.id).order_by(model.ResourceRevision.revision_timestamp)
        res_revs = res_rev_q.all()
        first_res_rev = res_revs[0]
        if 'request=GetCapabilities&version=' in first_res_rev.url:
            print add_stat('First revision already was WMS', res, stats)
            continue

        # Identify bad revisions by the WMS URL parameters and author
        bad_res_revs = res_rev_q.filter(model.ResourceRevision.url.ilike('%?service=W%S&request=GetCapabilities&version=%')).all()
        if bad_res_revs and \
           bad_res_revs[0].revision.author not in ('co-prod3.dh.bytemark.co.uk', 'current_revision_fixer2'):
            print add_stat('Misidentified', res, stats, 'author=%r' % bad_res_revs[0].revision.author)
            continue
        if not bad_res_revs:
            add_stat('Resource ok', res, stats)
            continue
        print ' ' # don't overwrite progress bar
        print add_stat('Bad revisions', res, stats, '(%d/%d)' % (len(bad_res_revs), len(res_revs)))
        total_bad_revisions += len(bad_res_revs)

        # Find the new latest (good) revision
        bad_res_revs_set = set(bad_res_revs)
        for res_rev_index in reversed(xrange(len(res_revs))):
            if res_revs[res_rev_index] not in bad_res_revs_set:
                latest_good_res_rev = res_revs[res_rev_index]
                break
        else:
            print add_stat('No good revisions', res, stats)
            continue
        if not options.write:
            continue

        # Delete the revisions and resource_revisions
        print '  Deleting bad revisions...'
        def delete_bad_revisions(res_revs):
            # Build the sql as a list, as it is faster when you have 1000 strings to append
            sql = ['''BEGIN;
            ALTER TABLE package_tag DROP CONSTRAINT package_tag_revision_id_fkey;
            ALTER TABLE package_extra DROP CONSTRAINT package_extra_revision_id_fkey;
            ALTER TABLE resource DROP CONSTRAINT resource_revision_id_fkey;
            ''']
            for res_rev in res_revs:
                sql.append("DELETE from resource_revision where id='%s' and revision_id='%s';\n" % (res.id, res_rev.revision_id))
                # a revision created (e.g. over the API) can be connect to other
                # resources or a dataset, so only delete the revision if only
                # connected to this one.
                if model.Session.query(model.ResourceRevision).\
                        filter_by(revision_id=res_rev.revision_id).\
                        count() == 1 and \
                        model.Session.query(model.PackageRevision).\
                        filter_by(revision_id=res_rev.revision_id).count() == 0:
                    sql.append("DELETE from revision where id='%s';\n" % res_rev.revision_id)
            sql.append("UPDATE resource SET revision_id='%s' WHERE id='%s';\n" % \
                (latest_good_res_rev.revision_id, res.id))
            sql.append('''
            ALTER TABLE package_tag ADD CONSTRAINT package_tag_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);
            ALTER TABLE package_extra ADD CONSTRAINT package_extra_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);
            ALTER TABLE resource ADD CONSTRAINT resource_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES revision(id);
            COMMIT;''')
            print '  sql..',
            model.Session.execute(''.join(sql))
            print '.committed'
            model.Session.remove()
        def chunks(l, n):
            '''Yield successive n-sized chunks from l.'''
            for i in xrange(0, len(l), n):
                yield l[i:i+n]
        # chunk revisions in chunks to cope when there are so many
        widgets = ['Creating SQL: ', Counter(),
                   'k/%sk ' % int(float(len(bad_res_revs))/1000.0), Bar(),
                   ' ', ETA()]
        progress2 = ProgressBar(widgets=widgets, maxval=int(float(len(bad_res_revs))/1000.0) or 1)
        for chunk_of_bad_res_revs in progress2(chunks(bad_res_revs, 1000)):
            delete_bad_revisions(chunk_of_bad_res_revs)

        # Knit together the remaining revisions again
        print '  Knitting existing revisions back together...'
        res_rev_q = model.Session.query(model.ResourceRevision).filter_by(id=res.id).order_by(model.ResourceRevision.revision_timestamp)
        res_revs = res_rev_q.all()
        latest_res_rev = res_revs[-1]
        if not latest_res_rev.current:
            latest_res_rev.current = True
        for i, res_rev in enumerate(res_revs[:-1]):
            if res_rev.expired_timestamp != res_revs[i+1].revision_timestamp:
                res_rev.expired_timestamp = res_revs[i+1].revision_timestamp
                res_rev.expired_id = res_revs[i+1].revision_id
        if latest_res_rev.expired_timestamp != END_OF_TIME:
            latest_res_rev.expired_timestamp = END_OF_TIME
        if latest_res_rev.expired_id is not None:
            latest_res_rev.expired_id = None

        # Correct the URL on the resource
        model.Session.query(model.Resource).filter_by(id=res.id).update({'url': latest_res_rev.url})
        model.repo.commit_and_remove()
        print '  ...done'


    print 'Summary\n', stats.report()
    print 'Total bad revs: %d' % total_bad_revisions
    if options.write and need_to_commit:
        model.repo.commit_and_remove()
        print 'Written'

def add_stat(outcome, res, stats, extra_info=None):
    res_id = '%s %s' % (res.resource_group.package.name, res.id[:4])
    if extra_info:
        res_id += ' %s' % extra_info
    return stats.add(outcome, res_id)


if __name__ == '__main__':
    usage = """Tool for removing wrong WMS revisions #1375

    usage: %prog [options] <ckan.ini>
    """
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-r', '--resource', dest='resource')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments (%i)' % len(args))
    config_ini = args[0]
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
    wms_revisions(options)
