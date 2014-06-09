'''Tool that takes a CSV containing resource URLs and corrected URLs and
updates DGU via the ORM. It is currently specific to the National Statistics
Publication Hub because of its title matching.

The CSV should have three columns with header:
"NS Title", "Bad link", "Good link"
'''
import csv
from optparse import OptionParser

from ckanext.dgu.bin import common
from ckanext.dgu.bin.running_stats import StatsList


def fix_links(csv_filepath, write=False):
    from ckan import model
    stats = StatsList()
    if write:
        rev = model.repo.new_revision()
        rev.author = 'Link fix from CSV'
        needs_commit = False
    with open(csv_filepath, 'rU') as f:
        reader = csv.reader(f)
        header = reader.next()
        assert header == ['NS Title', 'Bad link', 'Good link'], header
        for row in reader:
            ns_title, bad_link, good_link = row
            # Find the package and resource
            pkg_title = ns_title.split(' - ')[0]
            res_title = ' - '.join(ns_title.split(' - ')[1:])
            pkgs = model.Session.query(model.Package)\
                        .filter_by(title=pkg_title)\
                        .filter_by(state='active')\
                        .filter(model.Package.notes.like('%Source agency%'))\
                        .all()
            if not pkgs:
                print stats.add('Package title did not match', ns_title)
                continue
            if len(pkgs) > 1:
                print stats.add('Multiple package title matches', ns_title)
                continue
            pkg = pkgs[0]
            for res_ in pkg.resources:
                if res_.description[:len(res_title)] == res_title and 'hub-id' in res_.extras:
                    res = res_
                    break
            else:
                print stats.add('Resource title did not match', ns_title)
                continue
            # Update the link
            if res.url == good_link:
                print stats.add('Resource URL already fixed', ns_title)
                continue
            if res.url != bad_link and res.url.startswith('http://webarchive.nationalarchives.gov.uk'):
                print stats.add('Resource is already pointing to the webarchive - leave it', ns_title)
                continue
            if res.url != bad_link:
                print stats.add('Resource URL is not expected', ns_title)
                continue
            if write:
                print stats.add('Update link (written)', ns_title)
                res.url = good_link
                needs_commit = True
            else:
                print stats.add('Update link (not written)', ns_title)
    print stats.report()
    if write and needs_commit:
        model.repo.commit_and_remove()


if __name__ == '__main__':
    usage = __doc__ + """
usage:

%prog [-w] <broken_links.csv> <ckan.ini>
"""
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments (%i)' % len(args))
    csv_filepath, config_filepath = args
    print 'Loading CKAN config...'
    common.load_config(config_filepath)
    common.register_translator()
    print 'Done'
    fix_links(csv_filepath, write=options.write)
