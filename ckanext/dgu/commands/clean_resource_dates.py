import logging
from ckan.lib.cli import CkanCommand
import sys
import os
import re
from datetime import datetime
import csv

log = logging.getLogger('ckanext')

class CleanResourceDates(CkanCommand):
    """
    Iterate through resources, cleaning up dates to conform to DD-MM-YYYY spec.
    Usage: clean_resource_dates.py
       Or: clean_resource_dates.py commit
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 1
    min_args = 0

    standard_date_regex   = re.compile('^\d\d-\d\d-\d\d\d\d$')
    iso_date_regex        = re.compile('^\d\d\d\d-\d\d-\d\d$')
    regex_month_and_year  = re.compile('^\d\d-\d\d\d\d$')
    regex_year_and_month  = re.compile('^\d\d\d\d-\d\d$')
    regex_one_digit_both  = re.compile('^\d-\d-\d\d\d\d$')
    regex_one_digit_month = re.compile('^\d\d-\d-\d\d\d\d$')
    regex_one_digit_day   = re.compile('^\d-\d\d-\d\d\d\d$')
    regex_two_digit_year  = re.compile('^\d\d-\d\d-\d\d$')
    regex_pure_year       = re.compile('^\d\d\d\d$')

    def __init__(self, name):
        super(CleanResourceDates, self).__init__(name)
        for x in fixed_by_hand.values():
            assert self._is_clean_date(x), x

    def command(self):
        self._load_config()

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
        model.repo.new_revision()
        log.info("Database access initialised")
        data = self._get_dates(model)
        log.info('Scanning and cleaning...')
        clean_map = { x : self._clean_date(x) for x in data.keys() }
        can_be_cleaned    = { old:new for (old,new) in clean_map.items() if new }
        cannot_be_cleaned = [ old for (old,new) in clean_map.items() if not new ]
        if len(cannot_be_cleaned):
            log.info('=============')
            for dirty in sorted(cannot_be_cleaned):
                log.info('Could not clean: %s' % dirty)
            log.info('=============')
        log.info('Summary:')
        log.info('  %d can be cleaned.' % len(can_be_cleaned) )
        log.info('  %d cannot be cleaned.' % len(cannot_be_cleaned) )
        log.info('-------------')
        log.info('Writing changelog.csv...')
        if commit:
            log.info('CHANGES WILL BE COMMITTED!')
        with open('changelog.csv','w') as f:
            writer = csv.writer(f)
            writer.writerow(['resource_id','old_date','iso_date'])
            for old_date,resource_list in data.items():
                iso_date = can_be_cleaned.get(old_date)
                if iso_date is None:
                    continue
                for resource_id in resource_list:
                    writer.writerow([resource_id,old_date,iso_date])
        log.info('Finished.')


    def _get_dates(self,model):
        log.info( 'Fetching metadata for %d resources...' % model.Session.query(model.Resource).count() )
        # Format: { 'Nov 2012': ['resource_id_1','resource_id_2'...], '28/01/01': [...] }
        out = {}
        for resource in model.Session.query(model.Resource):
            date = resource.extras.get('date')
            if date is None: continue
            out[date] = out.get(date,[])
            out[date].append( resource.id )
        log.info( 'Done. %d unique date strings found.' % len(out) )
        log.info( 'Validating:' )
        for key in out.keys():
            if self._is_clean_date(key):
                del out[key]
        log.info( '%d date strings failed to validate:' % len(out) )
        return out

    def _is_clean_date(self,datestring):
        if not self.iso_date_regex.match(datestring):
            return False
        try:
            datetime.strptime(datestring,'%Y-%m-%d')
            return True
        except:
            return False

    def _clean_date(self,datestring):
        original_datestring = datestring
        datestring = datestring.strip()
        datestring = datestring.replace('/','-')
        datestring = datestring.replace(' ','-')
        datestring = datestring.replace('January'   , '01')
        datestring = datestring.replace('Jan'       , '01')
        datestring = datestring.replace('February'  , '02')
        datestring = datestring.replace('Feb'       , '02')
        datestring = datestring.replace('March'     , '03')
        datestring = datestring.replace('Mar'       , '03')
        datestring = datestring.replace('April'     , '04')
        datestring = datestring.replace('Apr'       , '04')
        datestring = datestring.replace('May'       , '05')
        datestring = datestring.replace('June'      , '06')
        datestring = datestring.replace('July'      , '07')
        datestring = datestring.replace('August'    , '08')
        datestring = datestring.replace('Aug'       , '08')
        datestring = datestring.replace('September' , '09')
        datestring = datestring.replace('Sept'      , '09')
        datestring = datestring.replace('October'   , '10')
        datestring = datestring.replace('Oct'       , '10')
        datestring = datestring.replace('November'  , '11')
        datestring = datestring.replace('Nov'       , '11')
        datestring = datestring.replace('December'  , '12')
        datestring = datestring.replace('Dec'       , '12')
        if self.regex_pure_year.match(datestring):
            # 2013 becomes 01-01-2013
            datestring = '01-01-' + datestring
        if self.regex_year_and_month.match(datestring):
            # 2013-09 becomes 09-2013
            datestring = datestring[-2:] + '-' + datestring[:4]
        if self.regex_month_and_year.match(datestring):
            # 09-2013 becomes 01-09-2013
            datestring = '01-'+datestring
        if self.regex_one_digit_both.match(datestring):
            # 1-9-2013 becomes 01-09-2013
            datestring = '0' + datestring[:2] + '0' + datestring[2:]
        if self.regex_one_digit_month.match(datestring):
            # 01-9-2013 becomes 01-09-2013
            datestring = datestring[:3] + '0' + datestring[3:]
        if self.regex_one_digit_day.match(datestring):
            # 1-09-2013 becomes 01-09-2013
            datestring = '0' + datestring
        if self.regex_two_digit_year.match(datestring):
            # Look Ma! I'm solving the millenium bug!
            # 01-09-13 becomes 01-09-2013
            coerce_year = '20'
            if int(datestring[6:])>50:
                coerce_year = '19'
            datestring = datestring[:6] + coerce_year + datestring[6:]
        # dd-mm-YYYY becomes YYYY-mm-dd (ISO format)
        if self.standard_date_regex.match(datestring):
            datestring = datestring[6:] + '-' + datestring[3:5] + '-' + datestring[:2]
            assert self.iso_date_regex.match(datestring)
        if self._is_clean_date(datestring):
            return datestring
        return fixed_by_hand.get(original_datestring.strip())


fixed_by_hand = {
  '01/0Case Outcomes by Principal Offence Category - March 20135/2013': '2013-05-01',
 '01/12//2012': '2012-12-01',
 '02.04.2013': '2013-04-02',
 '02/11/ 2010': '2010-11-02',
 '1/01/13': '2013-01-01',
 '1/3/13': '2013-03-01',
 '1/4/13': '2013-04-01',
 '1/5/13': '2013-05-01',
 '10th June 2010': '2010-06-10',
 '10th March 2011': '2011-03-10',
 '11/7/13': '2013-07-11',
 '13/072012': '2012-07-13',
 '14/12.2012': '2012-12-14',
 '15/4/13': '2013-04-15',
 '16-MAY-2013': '2013-05-16',
 '17th July 2012': '2012-07-17',
 '18/10/213': '2013-10-18',
 '1971-2033': '2033-12-31',
 '1989-2010': '2010-12-31',
 '1990 -  current': '1990-01-01',
 '1990 - current': '1990-01-01',
 '1990-2012': '2012-12-31',
 '1990-current': '1990-01-01',
 '1991-current': '1991-01-01',
 '1994-2012': '2012-12-31',
 '1996-2011': '2011-12-31',
 '1996-2012': '2012-12-31',
 '1997-98 - 2010-11': '2012-12-31',
 '1998-onwards': '1998-01-01',
 '1999/00': '2000-12-31',
 '19th July 2011': '2011-07-19',
 '19th October 2012': '2012-10-19',
 '2000-2010': '2010-12-31',
 '2001-2011': '2011-12-31',
 '2004-2005': '2005-12-31',
 '2005-2006': '2006-12-31',
 '2006-2007': '2007-12-31',
 '2007-2008': '2008-12-31',
 '2008-2009': '2009-12-31',
 '2008-2011': '2011-12-31',
 '2009-10, Final release': '2010-12-31',
 '2009-2010': '2010-12-31',
 '2010-11, Final release': '2011-12-31',
 '2010-2011': '2011-12-31',
 '2011-2012': '2012-12-31',
 '2011/12 q4': '2012-12-31',
 '2012-13': '2013-12-31',
 '2012-2013': '2013-12-31',
 '2012/13': '2013-12-31',
 '2012/13 q2': '2013-12-31',
 '2012/13 q3': '2013-12-31',
 '22.3.2013': '2013-03-22',
 '22082013': '2013-08-22',
 '23/0/2013': '2013-01-23',
 '24/072012': '2012-07-24',
 '28.08.2013': '2013-08-28',
 '28/02.2011': '2011-02-28',
 '280/02/2013': '2013-02-28',
 '30/0/2013': '2013-01-30',
 '30/062012': '2012-06-30',
 '30/09/20111': '2011-09-30',
 '31/02/2013': '2013-02-28',
 '31/05/02012': '2012-05-31',
 '31/05/201230/06/201231/07/2012': '2012-05-31',
 '31/052012': '2012-05-31',
 '31/06/2011': '2011-06-30',
 '44/03/13': '2013-03-01',
 '4th April 2012': '2012-04-04',
 '9th December 2011': '2011-12-09',
 'All': '2013-01-01',
 'Apr 2011-Mar 2012': '2012-03-31',
 'Apr-Sep 2012': '2012-09-30',
 'April - August 2011': '2011-08-31',
 'April - June 2010': '2010-06-30',
 'April - June 2011': '2011-06-30',
 'April 2010 to December 2010, Q3': '2010-12-31',
 'April 2010 to June 2010, Q1': '2010-06-30',
 'April 2010 to March 2011, Annual report': '2011-03-31',
 'April 2011 to December 2011, Q3': '2011-12-31',
 'April 2011 to June 2011, Q1': '2011-06-30',
 'April 2011 to September 2011, Q2': '2011-09-30',
 'April 2012 - March 2013': '2013-03-31',
 'April to June 2009': '2009-06-30',
 'April to June 2010': '2010-06-30',
 'April to June 2011': '2011-06-30',
 'April to June 2012': '2012-06-30',
 'Autumn 2012': '2012-09-30',
 'Current': '2013-01-01',
 'End Sept 2012': '2012-09-30',
 'Febriuary 2012': '2012-02-01',
 'Febuary 2013': '2013-02-01',
 'Feburary 2011': '2011-02-01',
 'January - March 2011': '2011-03-31',
 'January to March 2010': '2010-03-31',
 'January to March 2011': '2011-03-31',
 'January to March 2012': '2012-03-31',
 'January to March 2013': '2013-03-31',
 'July - September 2010': '2010-09-30',
 'July - September 2011': '2011-09-30',
 'July to September 2009': '2009-09-30',
 'July to September 2010': '2010-09-30',
 'July to September 2011': '2011-09-30',
 'May 2010 - March 2011': '2011-03-31',
 'N/A': '2013-01-01',
 'Nov 2010 to Dec 2011': '2011-12-31',
 'November 2010 to September 2011': '2011-09-30',
 'November to December 2010': '2010-12-31',
 'October - December 2010': '2010-12-31',
 'October - December 2011': '2011-12-31',
 'October to December 2009': '2009-12-31',
 'October to December 2010': '2010-12-31',
 'October to December 2011': '2011-12-31',
 'October to December 2012': '2012-12-31',
 'Q1, April 2011 to June 2011': '2011-06-30',
 'Q2 provisional and Q1 final 2011-12': '2012-03-31',
 'Q3 final 2011-12 and Q4 provisional 2011-12': '2012-12-31',
 'Q3, 2010-11': '2011-09-30',
 'Q3, 2011-12': '2012-09-30',
 'Q4, 2010-11': '2011-12-31',
 'Q4, 2011-12': '2012-12-31',
 'September to November 2010': '2010-11-30',
 'Table 115 Dwelling stock': '2013-01-01',
 'Table 691a': '2013-01-01',
}

