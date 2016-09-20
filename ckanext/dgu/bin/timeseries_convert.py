import re
import dateutil.parser
import datetime

from running_stats import Stats


MONTHS = 'jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july' \
    '|aug|august|sep|sept|september|oct|october|nov|november|dec|december|' \
    '1|2|3|4|5|6|7|8|9|10|11|12|01|02|03|04|05|06|07|08|09'


def add_date_to_resources(resources, just_year=False, dataset=None,
                          stats=None):
    '''Given a list of resource dicts, it tries to add a date value to them
    all.

    Specify just_year if it is an annual dataset and you want to ignore months.

    Specify a dataset if you want to look for dates in its title/description -
    suitable if you are merging several datasets into a series.
    '''
    stats = stats or Stats()
    for resource in resources:
        parsed_date = False
        if not just_year:
            # month and year
            for field_name, field_value in fields_to_hunt_for_date(resource,
                                                                   dataset):
                month, year = hunt_for_month_and_year(field_value)
                if year and month:
                    resource['date'] = '%02d/%s' % (month, year)
                    stats.add('Found date in %s' % field_name,
                              '%s %r' % (resource['date'], resource))
                    if resource.get('resource_type') == 'documentation':
                        resource['resource_type'] = 'file'
                        stats.add('Converted additional resource', resource)
                    parsed_date = True
                    break

        if not parsed_date:
            for field_name, field_value in fields_to_hunt_for_date(resource):

                # year
                year = re.search(r'\b(20\d{2})\b', field_value)
                if year:
                    resource['date'] = year.groups()[0]
                    stats.add('Found date in %s' % field_name,
                              '%s %r' % (resource['date'], resource))
                    if resource.get('resource_type') == 'documentation':
                        resource['resource_type'] = 'file'
                        stats.add('Converted additional resource', resource)
                    parsed_date = True
                    break

        if not parsed_date:
            if resource.get('resource_type') == 'documentation':
                stats.add('Could not find date but it\'s an Additional '
                                'Resource', resource)
                continue
            stats.add('Could not find date', resource)
            continue
    return stats


def fields_to_hunt_for_date(res, dataset=None):
    '''Given a resource, returns field key/values in the order they should be
    searched for dates.

    Will fall back to the dataset's fields too, if there is only one resource
    in the dataset and you are merging several together.
    '''
    date = res.get('date')
    if date:
        yield 'date', date
    title = res.get('title')
    if title:
        yield 'title', title
    yield 'description', res['description']
    yield 'url', re.sub('(%20|-|_|\.)', ' ', res['url'])
    if dataset:
        yield 'dataset-title', dataset['title']
        yield 'dataset-notes', dataset['notes']


def hunt_for_month_and_year(field_value):
    # 2/2013
    # 1/2/2013
    month_year_match = re.search(
        r'(?:\b|\b\d{1,2}[-/])(%s)[-/](20\d{2})\b' % MONTHS, field_value)
    if month_year_match:
        month, year = month_year_match.groups()
        return parse_month_as_word(month, int(year))

    # 2/13
    this_year_2_digits = datetime.datetime.now().year - 2000
    month_2_digit_year_match = re.search(
        r'\b(%s)[-/ ]?(\d{2})\b' % MONTHS,
        field_value, flags=re.IGNORECASE)
    if month_2_digit_year_match:
        month, year = month_2_digit_year_match.groups()
        year = int(year)
        if year > 9 and year < this_year_2_digits + 10:
            return parse_month_as_word(month, year + 2000)

    # 1/2/13
    # 13/2/1
    day_month_2_digit_year_match = re.search(
        r'\b(\d{1,2})[-/](%s)[-/ ]?(\d{2})\b' % MONTHS,
        field_value, flags=re.IGNORECASE)
    if day_month_2_digit_year_match:
        first, month, last = day_month_2_digit_year_match.groups()
        first = int(first)
        last = int(last)
        this_year_2_digits = datetime.datetime.now().year - 2000
        if last <= this_year_2_digits and first > this_year_2_digits:
            year = last
            return parse_month_as_word(month, year + 2000)
        elif first <= this_year_2_digits and last > this_year_2_digits:
            year = first
            return parse_month_as_word(month, year + 2000)
        elif 1 <= first <= 31 and last < this_year_2_digits + 10:
            # dd/mm/yy is far more likely than yy/mm/dd
            year = last
            return parse_month_as_word(month, year + 2000)

    # 2013/2
    year_month_match = re.search(
        r'\b(20\d{2})[-/](\d{1,2})(?:\b|\d{1,2}[-/]\b)', field_value)
    if year_month_match:
        year, month = year_month_match.groups()
        if int(month) < 13 and int(month) > 0:
            return int(month), int(year)

    year_match = re.search(r'\b(20\d{2})\b', field_value) or \
        re.search(r'\b(20\d{2})[-/]', field_value) or \
        re.search(r'[-/](20\d{2})\b', field_value)
    month_match = re.search(r'\b(%s)\b' % MONTHS, field_value,
                            flags=re.IGNORECASE)
    if year_match and month_match:
        return parse_month_as_word(month_match.groups()[0],
                                   year_match.groups()[0])
    return None, None


def parse_month_as_word(month_word, year):
    '''Also copes with a number'''
    month_digits_match = re.match('\d{1,2}', month_word)
    if month_digits_match:
        month = int(month_digits_match.group())
        return month, year
    month = month_word.lower().replace('sept', 'sep')
    month = month.replace('sepember', 'sep')
    month = month.replace('febuary', 'february')
    month = month.replace('february', 'february')
    month = month.replace('feburary', 'february')
    date_str = '1 %s %s' % (month, year)
    try:
        # dateutil converts '1 june 2014' to datetime(2014, 6, 1)
        # (we need the day or it won't parse 'february 2015' weirdly)
        date = dateutil.parser.parse(date_str)
    except ValueError:
        print 'ERROR parsing date: %s' % date_str
        import pdb; pdb.set_trace()
    return date.month, date.year

# Run with: python ckanext/dgu/bin/timeseries_convert.py
def test():
    from nose.tools import assert_equal
    assert_equal(hunt_for_month_and_year('21/10/11'), (10, 2011))
    assert_equal(hunt_for_month_and_year('a11-2014'), (None, None))
    assert_equal(hunt_for_month_and_year('11-2014'), (11, 2014))
    assert_equal(hunt_for_month_and_year('2014-11'), (11, 2014))
    assert_equal(hunt_for_month_and_year('nov 2014'), (11, 2014))
    assert_equal(hunt_for_month_and_year('April 2014'), (4, 2014))
    assert_equal(hunt_for_month_and_year('2014 nov'), (11, 2014))
    assert_equal(hunt_for_month_and_year('2014 Nov'), (11, 2014))
    assert_equal(hunt_for_month_and_year('2014 November'), (11, 2014))
    assert_equal(hunt_for_month_and_year('nov-14'), (11, 2014))
    assert_equal(hunt_for_month_and_year('nov14'), (11, 2014))

    # can't parse yet
    assert_equal(hunt_for_month_and_year('15-2014'), (None, None))

    # choose not to parse
    assert_equal(hunt_for_month_and_year('a2014'), (None, None))
    print 'ok'
test()