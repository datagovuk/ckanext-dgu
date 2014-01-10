import logging
from ckan.lib.cli import CkanCommand
import sys
import os
import re
from datetime import datetime
import csv
from ckan.lib.field_types import DateType,DateConvertError

class CleanResourceDates(CkanCommand):
    """
    Iterate through resources, cleaning up dates to conform to DateType YYYY-MM-DD database spec.
    Usage: clean_resource_dates.py
       Or: clean_resource_dates.py commit
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 1
    min_args = 0

    regex_date           = re.compile('^\d\d$')
    regex_year           = re.compile('^\d\d\d\d$')
    regex_year_month     = re.compile('^\d\d\d\d-\d\d$')
    regex_year_month_day = re.compile('^\d\d\d\d-\d\d-\d\d$')

    def __init__(self, name):
        super(CleanResourceDates, self).__init__(name)
        for x in fixed_by_hand.values():
            assert self._is_clean_date(x), x

    def command(self):
        self._load_config()

        # Logger is created here because you can't create the logger object
        # until the config is read, or it ends up .disabled and does nothing.
        log = self.log = logging.getLogger('ckanext.dgu.clean_resource_dates')

        commit = False
        if len(self.args)>0:
            if self.args[0]=='commit':
                commit = True
            else:
                log.info("Got strange args: " + str(self.args))
                sys.exit(1)
        else:
            log.info('Run with argument "commit" to actually change the database.')

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        log.info("Database access initialised")
        data = self._get_dates(model)
        log.info('Scanning and cleaning...')
        can_be_cleaned = {}
        cannot_be_cleaned = {}
        for key in data.keys():
            cleaned_key = self._clean_date(key)
            if self._is_clean_date(cleaned_key):
                can_be_cleaned[key] = cleaned_key
            else:
                cannot_be_cleaned[key] = cleaned_key
        if len(cannot_be_cleaned):
            log.info('=============')
            for dirty in sorted(cannot_be_cleaned.items(),key=lambda x:x[0]):
                log.info('FAIL: %s -> %s' % dirty)
            log.info('=============')
            log.info('FAIL: I cannot clean %d dates.' % len(cannot_be_cleaned))
            log.info('Update the script and try again.')
            log.info('Clean all dates at once to be safe. "2011-12" is ambiguous: It validates but it needs cleaning.')
            exit()
        log.info('Writing changelog.csv...')
        if commit:
            log.info('CHANGES WILL BE COMMITTED!')
            model.Session.remove()
            model.Session.configure(bind=model.meta.engine)
            rev = model.repo.new_revision()
            rev.author = 'Date format tidier'
        with open('changelog.csv','w') as f:
            writer = csv.writer(f)
            writer.writerow(['resource_id','old_date','iso_date'])
            for old_date,new_date in can_be_cleaned.items():
                for resource in data[old_date]:
                    writer.writerow([resource.id,old_date,new_date])
                    if commit:
                        resource.extras['date'] = new_date
                        model.Session.add(resource)
        if commit:
            log.info('Review changes that were made in changelog.csv.')
            log.info('Committing...')
            model.Session.commit()
        else:
            log.info('Review changes to be made in changelog.csv.')
            log.info('Re-run with argument "commit" to apply.')
        log.info('Finished.')

    def _get_dates(self,model):
        log = self.log
        resources = model.Session.query(model.Resource) \
                                 .filter_by(state='active') \
                                 .join(model.ResourceGroup) \
                                 .join(model.Package) \
                                 .filter_by(state='active') \
                                 .all()
        log.info( 'Fetching metadata for %d resources...' % len(resources) )
        # Format: { 'Nov 2012': ['resource_id_1','resource_id_2'...], '28/01/01': [...] }
        out = {}
        for resource in resources:
            date = resource.extras.get('date')
            if date is None: continue
            out[date] = out.get(date,[])
            out[date].append( resource )
        log.info( 'Done. %d unique date strings found.' % len(out) )
        log.info( 'Validating:' )
        #for key in out.keys():
        #    if self._is_clean_date(key):
        #        log.info('Already clean: '+key)
        #        del out[key]
        return out

    def _is_clean_date(self,db_string):
        if not self.regex_year.match(db_string) \
                and not self.regex_year_month.match(db_string) \
                and not self.regex_year_month_day.match(db_string):
                    return False
        try:
            parsed = DateType.parse_timedate(db_string,'db')
            assert parsed['readable_format'] in ['YYYY','YYYY-MM','YYYY-MM-DD']
            if parsed['readable_format'] in ['YYYY-MM','YYYY-MM-DD']:
                assert parsed['month'] in range(1,13)
            if parsed['readable_format'] == 'YYYY-MM-DD':
                assert parsed['day'] in range(1,32)
            assert parsed['year'] in range(1900,2100)
            return True
        except (DateConvertError,AssertionError), e:
            return False

    def _clean_date(self,datestring):
        original_datestring = datestring
        datestring = datestring.strip()
        # Fixed by hand overrides everything
        instant_win = fixed_by_hand.get(datestring)
        if instant_win is not None:
            return instant_win 
        # Perfect dates are already in unambiguous full ISO, eg. 2013-10-21. 
        # 2011-12 is NOT a perfect date. It needs cleaning, but it already conforms to schema. 
        is_perfect = self.regex_year_month_day.match(datestring)
        if is_perfect:
            return datestring
        datestring = datestring.replace('/',' ')
        datestring = datestring.replace('-',' ')
        datestring = datestring.replace('.',' ')
        tmp = datestring.split()
        (day,month,year) = (None,None,None)
        if len(tmp)==4 and tmp[0] in month_map and tmp[2] in month_map:
            # Handle "October to December 2012". Frequently happens.
            month = tmp[0]
            year = tmp[3]
        elif len(tmp)==3 and tmp[0] in month_map and tmp[1] in month_map:
            # Handle "October - December 2012". Semi-Frequently happens.
            month = tmp[0]
            year = tmp[2]
        elif len(tmp)==2 and self.regex_year.match(tmp[0]) and self.regex_date.match(tmp[1]):
            # Handle 2011-12. Ambiguous, but THAT IS NOT A MONTH!
            year  = tmp[0]
        elif len(tmp)==3:
            day   = tmp[0]
            month = tmp[1]
            year  = tmp[2]
        elif len(tmp)==2:
            month = tmp[0]
            year  = tmp[1]
        elif len(tmp)==1:
            year = tmp[0]
        else:
            return '[INVALID LENGTH] ' + datestring
        #---
        prefix = ''
        try:
            if day:
                day = self._clean_day(day)
            if month:
                month = self._clean_month(month)
            year = self._clean_year(year)
        except (ValueError,AssertionError) as e:
            prefix = '[%s] ' % str(e)
        if day:
            return '%s%s-%s-%s' % (prefix,year,month,day)
        if month:
            return '%s%s-%s' % (prefix,year,month)
        return '%s%s' % (prefix,year)

    def _clean_day(self,day):
        day = day.replace('th','')
        day = day.replace('st','')
        day = int(day)
        assert day in range(1,32)
        return '%02d' % day

    def _clean_month(self,month):
        if month in month_map:
            month = month_map[month]
        month = int(month)
        assert month in range(1,13)
        return '%02d' % month

    def _clean_year(self,year):
        year = int(year)
        if year<100:
            if year<50:
                year = 2000 + year
            else:
                year = 1900 + year
        assert year in range(1900,2100)
        return year


month_map = {
    'January'  : 1,
    'Jan'      : 1,
    'February' : 2,
    'Feb'      : 2,
    'Febriuary': 2,
    'Febuary'  : 2,
    'Feburary' : 2,
    'March'    : 3,
    'Mar'      : 3,
    'April'    : 4,
    'Apr'      : 4,
    'May'      : 5,
    'June'     : 6,
    'July'     : 7,
    'Jul'      : 7,
    'August'   : 8,
    'Aug'      : 8,
    'September': 9,
    'Sept'     : 9,
    'Sep'      : 9,
    'October'  : 10,
    'Oct'      : 10,
    'November' : 11,
    'Nov'      : 11,
    'December' : 12,
    'Dec'      : 12,
}

fixed_by_hand = {
    '01/0Case Outcomes by Principal Offence Category - March 20135/2013' : '2013-05-01',
    '05/11/2103' : '2013-11-05',
    '11/04/2102' : '2012-04-11',
    '16-MAY-2013' : '2013-05-16',
    '18/10/213' : '2013-10-18',
    '1990 -  current' : '1990',
    '1990 - current' : '1990',
    '1990-current' : '1990',
    '1991-current' : '1991',
    '1997-98 - 2010-11' : '1997',
    '1998-onwards' : '1998',
    '2009-10, Final release' : '2009-04',
    '2010-11, Final release' : '2010-04',
    '2011/12 q4' : '2012-01',
    '2012/13 q2' : '2012-07',
    '2012/13 q3' : '2012-10',
    '2012/13 q4' : '2013-01',
    '22082013' : '2013-08-22',
    '23/0/2013' : '2013-01-23',
    '280/02/2013' : '2013-02-28',
    '30/0/2013' : '2013-01-30',
    '30/08/2103' : '2013-08-30',
    '30/09/20111' : '2011-09-30',
    '31/05/201230/06/201231/07/2012' : '2012-05-31',
    'All' : '2013',
    'April 2010 to December 2010, Q3'         : '2010-04',
    'April 2010 to June 2010, Q1'             : '2010-04',
    'April 2010 to March 2011, Annual report' : '2010-04',
    'April 2011 to December 2011, Q3'         : '2011-04',
    'April 2011 to June 2011, Q1'             : '2011-04',
    'April 2011 to September 2011, Q2'        : '2011-04',
    'Autumn 2012' : '2012-09',
    'Current' : '2013',
    'End Sept 2012' : '2012-09',
    'N/A' : '2013',
    'Nov 2010 to Dec 2011' : '2010-11',
    'November 2010 to September 2011' : '2010-11',
    'Q1 2013/14' : '2013-04',
    'Q1, April 2011 to June 2011' : '2011-04',
    'Q2 2013/14' : '2013-07',
    'Q2 provisional and Q1 final 2011-12' : '2011-04',
    'Q3 2012/13' : '2012-10',
    'Q3 final 2011-12 and Q4 provisional 2011-12' : '2011-10',
    'Q3, 2010-11' : '2010-10',
    'Q3, 2011-12' : '2011-10',
    'Q4 2012/13' : '2013-01',
    #'Q4, 2010-11' : '2011-01',
    #'Q4, 2011-12' : '2012-01',
    #'Single file' : '2013',
    'Table 115 Dwelling stock' : '2013',
    'Table 691a' : '2013',
    '13/072012': '2012-07-13',
    '1971-2033': '1971',
    '1989-2010': '1989',
    '1990-2012': '1990',
    '1994-2012': '1994',
    '1996-2011': '1996',
    '1996-2012': '1996',
    '1999/00': '1999-04',
    '2000-2010': '2000',
    '2000/01': '2000-04',
    '2001-2011': '2001',
    '2001/02': '2001-04',
    '2002/03': '2002-04',
    '2003/04': '2003-04',
    '2004-2005': '2004-04',
    '2004/05': '2004-04',
    '2005-2006': '2005-04',
    '2005/06': '2005-04',
    '2006-2007': '2006-04',
    '2006/07': '2006-04',
    '2007-2008': '2007-04',
    '2007/08': '2007-04',
    '2008-2009': '2008-04',
    '2008-2011': '2008',
    '2008/09': '2008-04',
    '2009-2010': '2009-04',
    '2009/10': '2009-04',
    '2010-2011': '2010-04',
    '2010/11': '2010-04',
    '2011-2012': '2011-04',
    '2011/12': '2011-04',
    '2012-2013': '2012-04',
    '2012/13': '2012-04',
    '24/072012': '2012-07-24',
    '30/062012': '2012-06-30',
    '31/052012': '2012-05-31',
    '2103-10-18': '2013-10-18',
    '44/03/13': '2013-03',
    'Q4, 2010-11' : '2011-01',
    'Q4, 2011-12' : '2012-01',
    'Single file': '2013',
}
