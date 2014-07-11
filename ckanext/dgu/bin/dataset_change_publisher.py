'''Tool that moves all datasets from one publisher to another.
'''
from optparse import OptionParser

from ckanext.dgu.bin import common
from ckanext.dgu.bin.running_stats import StatsList


def change_publisher(from_publisher_name, to_publisher_name, options):
    from ckan import model
    stats = StatsList()
    if options.write:
        rev = model.repo.new_revision()
        rev.author = 'script_dataset_change_publisher'
        needs_commit = False
    from_publisher = model.Group.get(from_publisher_name)
    to_publisher = model.Group.get(to_publisher_name)
    datasets = common.get_datasets(dataset_name=options.dataset,
                                   organization_ref=from_publisher_name)
    assert to_publisher
    for dataset in datasets:
        member = model.Session.query(model.Member) \
                      .filter_by(group_id=from_publisher.id) \
                      .filter_by(table_name='package') \
                      .filter_by(table_id=dataset.id) \
                      .first()
        if member:
            print stats.add('Change owner_id and Member', dataset.name)
        else:
            print stats.add('Change owner_id but no Member', dataset.name)
        if options.write:
            dataset.owner_org = to_publisher.id
            if member:
                member.group_id = to_publisher.id
            needs_commit = True

    print stats.report()
    if options.write and needs_commit:
        model.repo.commit_and_remove()


if __name__ == '__main__':
    usage = __doc__ + """
usage:

%prog [-w] <pub_from> <pub_to> <ckan.ini>
"""
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    parser.add_option('-d', '--dataset', dest='dataset')
    (options, args) = parser.parse_args()
    if len(args) != 3:
        parser.error('Wrong number of arguments (%i)' % len(args))
    from_publisher_name, to_publisher_name, config_filepath = args
    print 'Loading CKAN config...'
    common.load_config(config_filepath)
    common.register_translator()
    print 'Done'
    change_publisher(from_publisher_name, to_publisher_name, options)

