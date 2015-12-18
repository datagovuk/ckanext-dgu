'''
Remove no longer used Resouce extra 'cache_filepath' and related.
'''
import math
from copy import deepcopy

import common
from optparse import OptionParser
from ckan import model

from running_stats import Stats

stats_rp = Stats()
stats_re = Stats()
stats_dp = Stats()
stats_de = Stats()

# These are ckan resource properties that an old version of the archiver filled
# in and are no longer updated. They are now stored in the Archival table.
res_properties_to_make_null = set((
    'cache_last_updated',
    'size',
    'hash',
    'last_modified',
    'mimetype',
    'cache_url',
    ))

# These are custom extra fields added by old versions of the archiver &
# qa, whereas now they store them in the Archival table.
res_extras_to_remove = set((
    'cache_filepath',
    'content_length',
    'content_type',
    'openness_score',
    'openness_score_failure_count',
    'openness_score_reason',
))

dataset_properties_to_make_null = set()

# These are custom extra fields added by old versions of the archiver &
# qa, whereas now they store them in the Archival table.
dataset_extras_to_remove = set((
    'openness_score',
    'openness_score_last_checked',
    'department',  # was taken over by agency/department then owner_org
    'agency',  # was taken over by agency/department then owner_org
    'published_by',  # was taken over by owner_org
    'published_via',  # was taken over by owner_org
))


class DeleteCacheFilepath(object):

    @classmethod
    def process_resource(self, resource):
        updated = False
        for key in res_properties_to_make_null:
            if getattr(resource, key):
                stats_rp.add('Making property null: %s' % key, resource.id)
                setattr(resource, key, None)
                updated = True
            else:
                stats_rp.add('Property has no value: %s' % key, resource.id)

        extras = deepcopy(resource.extras)
        for key in res_extras_to_remove:
            if key in extras:
                stats_re.add('Removing: %s' % key, resource.id)
                del extras[key]
                updated = True
            else:
                stats_re.add('No field to remove: %s' % key, resource.id)
        if updated:
            resource.extras = extras
        return updated

    @classmethod
    def command(cls, config_ini, write, options):
        common.load_config(config_ini)
        common.register_translator()

        rev = model.repo.new_revision()
        rev.author = 'script-delete_cache_filepath.py'

        process_all = True
        if options.resource:
            cls.process_resource(model.Resource.get(options.resource))
            process_all = False
        else:
            # Get each dataset,
            counter = 0
            datasets_q =  model.Session.query(model.Package) \
                    .filter_by(state='active')

            rounded = int(math.ceil(datasets_q.count() / 100.0)) * 100
            for x in xrange(0, rounded, 100):
                datasets = datasets_q.offset(x).limit(100)
                updated = False

                for dataset in datasets.all():
                    counter += 1

                    print "Processing dataset %d\r" % counter,
                    for resource in dataset.resources:
                        if cls.process_resource(resource):
                            updated = True

                    for key in dataset_properties_to_make_null:
                        if getattr(dataset, key):
                            stats_dp.add('Making property null: %s' % key, dataset.name)
                            setattr(dataset, key, None)
                            updated = True
                        else:
                            stats_dp.add('Property has no value: %s' % key, dataset.name)

                    for key in dataset_extras_to_remove:
                        if key in dataset.extras:
                            #stats_de.add('Removing: %s' % key, dataset.name)
                            del dataset.extras[key]
                            updated = True
                        else:
                            stats_de.add('No field to remove: %s' % key, dataset.name)

                # We will be committing 100 at a time
                if updated and write:
                    print "\nCommitting changes"
                    import time
                    s = time.time()
                    model.Session.commit()
                    print "Committed in ", time.time() - s

        print 'Resource Properties:\n', stats_rp.report(show_time_taken=False)
        print 'Resource Extras:\n', stats_re.report()
        print 'Dataset Properties:\n', stats_dp.report(show_time_taken=False)
        print 'Dataset Extras:\n', stats_de.report()


usage = __doc__ + '''
Usage:
    python delete_cache_filepath.py <CKAN config ini filepath> [--write]'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-r', '--resource', dest='resource')
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes to the datasets")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]
    DeleteCacheFilepath.command(config_ini, options.write, options)
