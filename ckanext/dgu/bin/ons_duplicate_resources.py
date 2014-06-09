'''
Some Nat Stats Pub Hub datasets have duplicate resources. Some may have got
created wrongly and will need merging.
'''

from optparse import OptionParser
from pprint import pprint

from ckanext.dgu.bin import common
from ckanext.dgu.bin.running_stats import StatsList


def fix_duplicates(options):
    from ckan import model
    from ckanext.archiver.model import Archival
    write = options.write
    if write:
        rev = model.repo.new_revision()
        rev.author = 'Fix duplicate resources'
        needs_commit = False
    stats = StatsList()
    pkgs = model.Session.query(model.Package)\
                .filter_by(state='active')\
                .join(model.PackageExtra)\
                .filter_by(state='active')\
                .filter_by(key='external_reference')\
                .filter_by(value='ONSHUB')\
                .order_by(model.Package.name)
    if options.dataset:
        pkg = model.Package.get(options.dataset)
        pkgs = pkgs.filter(model.Package.id==pkg.id)
    pkgs = pkgs.all()
    for pkg in pkgs:
        previous_resources = {}

        def get_res_properties(resource):
            return {'url': resource.url,
                    'hub-id': resource.extras.get('hub-id'),
                    'date': resource.extras.get('date'),
                    'publish-date': resource.extras.get('publish-date')}

        def is_res_broken(resource):
            archival = Archival.get_for_resource(resource.id)
            if not archival:
                return None
            return archival.is_broken

        has_duplicates = False
        if not pkg.resources:
            print stats.add('No resources', pkg.name)
        for res in pkg.resources:
            res_properties = get_res_properties(res)
            res_identity = '%s %s' % (pkg.name, res.description)
            if res.description in previous_resources:
                has_duplicates = True
                prev_res = previous_resources[res.description]
                prev_res_properties = get_res_properties(prev_res)
                if res_properties == prev_res_properties:
                    needs_commit=True
                    print stats.add('Resource indentical - dedupe', res_identity)
                    merge_resources((res, prev_res), write)
                elif prev_res_properties['date'] != res_properties['date']:
                    print stats.add('Resource same description, different date in timeseries - ok', res_identity)
                elif prev_res_properties['hub-id'] and res_properties['hub-id'] and prev_res_properties['hub-id'] != res_properties['hub-id']:
                    print stats.add('Resource same description, different hub-id - ok', res_identity)
                elif prev_res_properties['hub-id'] and prev_res_properties['hub-id'] == res_properties['hub-id']:
                    needs_commit=True
                    print stats.add('Resource with same hub-id - merge', res_identity)
                    pprint(prev_res_properties)
                    pprint(res_properties)
                    merge_resources((res, prev_res), write)
                elif prev_res_properties['url'] == res_properties['url']:
                    needs_commit=True
                    print stats.add('Resource same description & url, different other properties - merge', res_identity)
                    pprint(prev_res_properties)
                    pprint(res_properties)
                    merge_resources((res, prev_res), write)
                elif is_res_broken(prev_res) or is_res_broken(res):
                    print stats.add('Resource same description, different properties, some breakage - delete one', res_identity)
                    if is_res_broken(prev_res):
                        print 'BROKEN:'
                    pprint(prev_res_properties)
                    if is_res_broken(res):
                        print 'BROKEN:'
                    pprint(res_properties)
                else:
                    print stats.add('Resource same description, different properties - manual decision', res_identity)
                    pprint(prev_res_properties)
                    pprint(res_properties)
            previous_resources[res.description] = res

        if not has_duplicates:
            print stats.add('Package without duplicates', pkg.name)
    print stats.report()
    if write and needs_commit:
        print 'Writing...'
        model.repo.commit_and_remove()
        print '...done'
    elif write:
        print 'Nothing to write'
    else:
        print 'Not written'

def merge_resources(resources, write):
    assert len(resources) == 2
    # Keep the one with hub-id
    if resources[0].extras.get('hub-id'):
        keep_res = resources[0]
        other_res = resources[1]
    else:
        keep_res = resources[1]
        other_res = resources[0]
    # Merge properties
    core_properties = ('format', 'description', 'url')
    for key in core_properties:
        keep_val = getattr(keep_res, key)
        other_val = getattr(other_res, key)
        if other_val and other_val != keep_val:
            if not keep_val:
                if write:
                    setattr(keep_res, key, other_val)
                print '  merge: %s=%s' % (key, other_val)
            else:
                print '  WARN: discard %s %s in favour of %s' % (key, other_val, keep_val)
    ignore_extras = set(('cache_last_updated', 'cache_filepath', 'cache_url', 'datastore_active'))
    for key in set(other_res.extras) - ignore_extras:
        keep_val = keep_res.extras.get(key)
        other_val = other_res.extras[key]
        if other_val and other_val != keep_val:
            if not keep_val:
                if write:
                    keep_res.extras[key] = other_val
                print '  merge: %s %s' % (key, other_val)
            else:
                print '  WARN: discard %s %s in favour of %s' % (key, other_val, keep_val)
    if write:
        other_res.state = 'deleted'

if __name__ == '__main__':
    usage = __doc__ + """
usage:

%prog [-w] <ckan.ini>
"""
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    parser.add_option('-d', '--dataset', dest='dataset')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments (%i)' % len(args))
    config_filepath = args[0]
    print 'Loading CKAN config...'
    common.load_config(config_filepath)
    common.register_translator()
    print 'Done'
    fix_duplicates(options)

