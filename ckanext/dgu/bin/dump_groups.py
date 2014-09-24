'''Tool that dumps all the group data to CSV, for the current state of the db
or an earlier date.
'''
from optparse import OptionParser
import datetime
import csv
import StringIO

from sqlalchemy.sql import select

from ckan.lib.dictization import obj_list_dictize, model_dictize
from ckanext.dgu.bin import common
#from ckanext.dgu.bin.running_stats import StatsList


def dump_groups(date, options):
    from ckan import model

    # column headings
    header = ['name', 'id', 'title']
    headings_all = set(header)
    headings_main = set()
    headings_extra = set()

    # get the groups
    group_rev_table = model.group_revision_table
    q = select([group_rev_table])
    if options.organization:
        q = q.where(group_rev_table.c.name==options.organization)
    context = {'model': model, 'session': model.Session,
               'revision_date': date}
    result = model_dictize._execute_with_revision(q, group_rev_table, context)
    groups = obj_list_dictize(result, context)
    # just double check there are no deleted ones in the list
    for group in groups:
        assert group['state'] == 'active'
    print '%i groups' % len(groups)

    for group in groups:
        # get the group extras
        group_extra_rev_table = model.group_extra.group_extra_revision_table
        q = select([group_extra_rev_table]) \
            .where(group_extra_rev_table.c.group_id == group['id'])
        result = model_dictize._execute_with_revision(q, group_extra_rev_table,
                                                      context)
        extras = result.fetchall()
        for extra in extras:
            if extra['state'] == 'active':
                group['extra-%s' % extra['key']] = extra['value']
        #group['extras'] = model_dictize.extras_list_dictize(result, context)

        for delete_property in ['revision_timestamp', 'revision_id']:
            del group[delete_property]

        # get the parent group
        member_rev_table = model.member_revision_table
        q = select([member_rev_table]) \
            .where(member_rev_table.c.group_id == group['id']) \
            .where(member_rev_table.c.table_name == 'group')
        result = model_dictize._execute_with_revision(q, member_rev_table,
                                                      context)
        parents = result.fetchall()
        for parent in parents:
            if parent['state'] == 'active':
                parent_group = model.Group.get(parent['table_id'])
                group['parent'] = parent_group.name
        # member revisions seem to miss a good number, so default to the current parent
        if 'parent' not in group:
            members = model.Session.query(model.Member) \
                           .filter_by(group_id=group['id']) \
                           .filter_by(table_name='group') \
                           .all()
            if members:
                parent_group = model.Group.get(members[0].table_id)
                if parent_group:
                    group['parent'] = parent_group.name

        # column headings
        for key in group.keys():
            if key not in headings_all:
                if key.startswith('extra-'):
                    headings_extra.add(key)
                else:
                    headings_main.add(key)
                headings_all.add(key)

    groups.sort(key=lambda g: g['name'])
    header += sorted(headings_main) + sorted(headings_extra)

    # write CSV
    csv_filepath = date.strftime(options.filename or 'groups-%Y-%m-%d.csv')
    #csv_filepath = options.filename or 'groups.csv'
    print 'Writing %s' % csv_filepath
    with open(csv_filepath, 'w') as f:
        w = UnicodeDictWriter(f, header, encoding='utf8')
        w.writerow(dict(zip(header, header)))
        w.writerows(groups)


class UnicodeWriter(object):
    """
    Like UnicodeDictWriter, but takes lists rather than dictionaries.

    Usage example:

    fp = open('my-file.csv', 'wb')
    writer = UnicodeWriter(fp)
    writer.writerows([
        [u'Bob', 22, 7],
        [u'Sue', 28, 6],
        [u'Ben', 31, 8],
        # \xc3\x80 is LATIN CAPITAL LETTER A WITH MACRON
        ['\xc4\x80dam'.decode('utf8'), 11, 4],
    ])
    fp.close()
    """
    def __init__(self, f, dialect=csv.excel, encoding="utf8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoding = encoding

    def writerow(self, row):
        # Modified from original: now using unicode(s) to deal with e.g. ints
        self.writer.writerow([unicode(s).encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = data.encode(self.encoding)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class UnicodeDictWriter(UnicodeWriter):
    """
    A CSV writer that produces Excel-compatibly CSV files from unicode data.
    Uses UTF-16 and tabs as delimeters - it turns out this is the only way to
    get unicode data in to Excel using CSV.

    Usage example:

    fp = open('my-file.csv', 'wb')
    writer = UnicodeDictWriter(fp, ['name', 'age', 'shoesize'])
    writer.writerows([
        {'name': u'Bob', 'age': 22, 'shoesize': 7},
        {'name': u'Sue', 'age': 28, 'shoesize': 6},
        {'name': u'Ben', 'age': 31, 'shoesize': 8},
        # \xc3\x80 is LATIN CAPITAL LETTER A WITH MACRON
        {'name': '\xc4\x80dam'.decode('utf8'), 'age': 11, 'shoesize': 4},
    ])
    fp.close()

    Initially derived from http://docs.python.org/lib/csv-examples.html
    """

    def __init__(self, f, fields, dialect=csv.excel,
                 encoding="utf-8", **kwds):
        super(UnicodeDictWriter, self).__init__(f, dialect, encoding, **kwds)
        self.fields = fields

    def writerow(self, drow):
        row = [drow.get(field, '') for field in self.fields]
        super(UnicodeDictWriter, self).writerow(row)


if __name__ == '__main__':
    usage = __doc__ + """
usage:

%prog [-w] [YY-MM-DD|all] <ckan.ini>
"""
    parser = OptionParser(usage=usage)
    #parser.add_option("-w", "--write",
    #                  action="store_true", dest="write",
    #                  help="write the theme to the datasets")
    parser.add_option('-f', '--filename', dest='filename')
    parser.add_option('-o', '--organization', dest='organization')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments (%i)' % len(args))
    date_str, config_filepath = args
    print 'Loading CKAN config...'
    common.load_config(config_filepath)
    common.register_translator()
    print 'Done'
    if date_str == 'all':
        now = datetime.date.today()
        date = datetime.date(2012, 6, 1)
        while date <= now:
            dump_groups(date, options)
            date += datetime.timedelta(days=31)
            while date.day != 1:
                date -= datetime.timedelta(days=1)
    else:
        date = datetime.date(*[int(chunk) for chunk in date_str.split('-')])
        dump_groups(date, options)
