'''
Takes an SQL dump file and anonymizes the Users' details - email, apikey,
fullname, reset_key and passwords to a given one. Works with gzipped input and
output files.

The resulting SQL can then be safely transferred to and used on test machines
and developer boxes, without worrying about security of the email addresses or
password hashes being compromized from there.
'''
from optparse import OptionParser
import re
from hashlib import sha1
import sys
import gzip

OPTION_DEFAULTS = {
    'password': 'pass',
    'email': 'dgutesting+{name}@gmail.com',
    'apikey': '{name}-apikey'
    }

def password_hasher(password_8bit):
    # This is CKAN's hasher, as it is now
    salt = sha1('test_salt')
    hash = sha1(password_8bit + salt.hexdigest())
    hashed_password = salt.hexdigest() + hash.hexdigest()
    return hashed_password


def open_(filepath, *args):
    '''A wrapper around open() or gzip.open(), depending on if the filename
    extension is .gz'''
    if filepath.endswith('.gz'):
        return gzip.open(filepath, *args)
    return open(filepath, *args)


def anonymize_files(input_filepath, output_filepath, **options):
    with open_(input_filepath, 'rb') as in_file:
        with open_(output_filepath, 'wb') as out_file:
            num_users = anonymize(in_file, out_file, **options)
    return num_users


def anonymize(input_file, output_file, **options):
    for key in OPTION_DEFAULTS:
        if options.get(key) is None:
            options[key] = OPTION_DEFAULTS[key]
    password_hash = password_hasher(options['password'])
    in_users_table = False
    start_of_user_table = re.compile('COPY \"user\" \((.*) FROM stdin;\n')
    number_of_users_done = 0
    columns = None
    column_indexes = None
    for line in input_file:
        if in_users_table:
            if line in ('\\.\n', '\n', '--\n'):
                in_users_table = False
                output_file.write(line)
                continue
            line_columns = line.rstrip('\n').split('\t')
            assert len(line_columns) == len(columns), \
                'Wrong num of columns: %s' % line
            params = {'name': line_columns[column_indexes['name']]}
            line_columns[column_indexes['email']] = options['email'].format(**params)
            line_columns[column_indexes['password']] = password_hash
            line_columns[column_indexes['reset_key']] = '\N'
            line_columns[column_indexes['apikey']] = options['apikey'].format(**params)
            line_columns[column_indexes['fullname']] = '\N'
            line = '\t'.join(line_columns) + '\n'
            number_of_users_done += 1
        elif start_of_user_table.match(line):
            columns_str = start_of_user_table.match(line).groups()[0]
            columns = columns_str.split(', ')
            column_indexes = dict(zip(columns, range(len(columns))))
            in_users_table = True
        output_file.write(line)
    return number_of_users_done


test_data = '''
--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: dgu
--

COPY "user" (id, name, apikey, created, about, openid, password, fullname, email, reset_key, sysadmin, activity_streams_email_notifications, state) FROM stdin;
2b703044-aaaa-bbbb-cccc-0494b6b5293c\timantonceam\t9209715b-aaaa-bbbb-cccc-99ad-e223797c0851\t2011-07-22 10:30:23.141703\t\N\t\N\t12345678971b1e8ea4da21af8a9a35d25b9eb7cd178c2f41e0cb4d607b9ef99c6302f17d08b7a676\timantonceam\timanton@cookermail.com\tIan\tf\tf\tactive
e17112db-aaaa-bbbb-cccc-cf23760514cd\tNawsNeard\t21eb326d-aaaa-bbbb-cccc-d7a9edc63ea1\t2011-07-22 22:26:38.857654\t\N\t\N\t123456789097f64c338c77d0f84a69a34d239e212e5f1c4920ff7b0bfadba81b6694257147f2e4f\tNawsNeard\tnawsneard@cookermail.com\t\N\tf\tf\tactive

--
COPY user_following_dataset (follower_id, object_id, datetime) FROM stdin;
\.
'''
expected_output = '''
--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: dgu
--

COPY "user" (id, name, apikey, created, about, openid, password, fullname, email, reset_key, sysadmin, activity_streams_email_notifications, state) FROM stdin;
2b703044-aaaa-bbbb-cccc-0494b6b5293c\timantonceam\timantonceamapikey\t2011-07-22 10:30:23.141703\t\N\t\N\tPASSWORD\t\N\ttest+imantonceam@com\t\N\tf\tf\tactive
e17112db-aaaa-bbbb-cccc-cf23760514cd\tNawsNeard\tNawsNeardapikey\t2011-07-22 22:26:38.857654\t\N\t\N\tPASSWORD\t\N\ttest+NawsNeard@com\t\N\tf\tf\tactive

--
COPY user_following_dataset (follower_id, object_id, datetime) FROM stdin;
\.
'''

# To run this test, do:
# python -c 'from ckanext.dgu.bin.anonymize_sql import test; test()'
def test():
    from nose.tools import assert_equal
    import cStringIO as StringIO
    out_file = StringIO.StringIO()
    options = {
            'password': 'pw',
            'email': 'test+{name}@com',
            'apikey': '{name}apikey'
        }
    num_users = anonymize(StringIO.StringIO(test_data), out_file, **options)
    assert_equal(num_users, 2)
    expected_output_ = expected_output.replace(
        'PASSWORD', password_hasher(options['password']))
    output = out_file.getvalue()
    if output != expected_output_:
        for i, output_line in enumerate(output.split('\n')):
            expected = expected_output_.split('\n')[i]
            if output_line != expected:
                print 'GOT:    ' + output_line
                print 'WANTED: ' + expected
                assert 0
    print 'success'


if __name__ == '__main__':
    usage = __doc__ + '\n\nUsage: %prog [options] input.sql output.sql'
    parser = OptionParser(usage=usage)
    parser.add_option('-p', '--password', dest='password', default=OPTION_DEFAULTS['password'])
    parser.add_option('-e', '--email', dest='email', default=OPTION_DEFAULTS['email'])
    parser.add_option('-a', '--apikey', dest='apikey', default=OPTION_DEFAULTS['apikey'])
    (options, args) = parser.parse_args()
    input_filepath, output_filepath = args
    num_users = anonymize_files(input_filepath, output_filepath, **vars(options))
    if num_users < 500:
        print 'Not enough users - some problem occurred'
        sys.exit(1)
