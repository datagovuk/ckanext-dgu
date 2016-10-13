#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Converts Organograms XLS files into a pair of CSVs: junior and senior posts.
Does verification of the structure and values.
'''

# The script is structured so that errors are appended to a list
# rather than going straight to stderr. The script can therefore
# be reused to fulfil an API endpoint (for example).

# pip install pandas==0.17.0
import pandas
import numpy
import sys
import os.path
import json
from xlrd import XLRDError
import csv
import re
import argparse
import string
import logging
import itertools

log = __import__('logging').getLogger(__name__)

args = None

class ValidationFatalError(Exception):
    pass


def load_excel_store_errors(filename, sheet_name, errors, validation_errors, input_columns, rename_columns, blank_columns, integer_columns, string_columns):
    """Carefully load an Excel file, taking care to log errors and produce clean output.
    You'll always receive a dataframe with the expected columns, though it might contain 0 rows if
    there are errors. Strings will be stored in the 'errors' array.
    If 'validation_errors' are inserted, it means some values are discarded, but you would not be prevented from displaying the rest of the data.
    """
    # Output columns can be different. Update according to the rename_columns dict:
    output_columns = [rename_columns.get(x,x) for x in input_columns]
    try:
        # need to convert strings at this stage or leading zeros get lost
        string_converters = dict((col, str) for col in string_columns)
        df = pandas.read_excel(filename,
                               sheet_name,
                               convert_float=True,
                               parse_cols=len(input_columns)-1,
                               converters=string_converters,
                               keep_default_na=False,
                               na_values=[''])
    except XLRDError, e:
        errors.append(str(e))
        return pandas.DataFrame(columns=output_columns)
    # Verify number of columns
    if len(df.columns)!=len(input_columns):
        errors.append("Sheet '%s' contains %d columns. I expect at least %d columns." % (sheet_name, len(df.columns), len(input_columns)))
        return pandas.DataFrame(columns=output_columns)
    # Blank out columns
    for column_name in blank_columns:
        col_index = df.columns.tolist().index(column_name)
        df.drop(df.columns[col_index], axis=1, inplace=True)
        df.insert(col_index, column_name, '')
    # Softly correct column names
    for i in range(len(df.columns)):
        # Check column names are as expected. Also allow them to be the renamed
        # version, since old XLS templates had "Grade" instead of "Grade (or
        # equivalent)" for senior sheet. (And the CSVs follow the same pattern
        # - during 2011 they had "Grade" and subsequently they were "Grade (or
        # equivalent)")
        if df.columns[i] != input_columns[i] and \
                output_columns[i] != input_columns[i]:
            from string import uppercase
            errors.append("Wrong column title. "
                          "Sheet '%s' column %s: Title='%s' Expected='%s'" %
                          (sheet_name, uppercase[i], df.columns[i],
                           input_columns[i]))
    df.columns = output_columns
    # Filter null rows
    # (defined as having the first two columns both blank. junior roles
    # generated from triplestore don't have a parent organization set.)
    df = df.dropna(subset=df.columns[0:2], how='all')
    # Softly cast to integer (or N/A or N/D)
    def validate_int_or_na(column_name):
        def _inner(x):
            if pandas.isnull(x):
                # i.e. float.NaN. Cell contained e.g. 'N/A'
                return 'N/A'
            try:
                return str(int(round(x)))
            except (TypeError, ValueError):
                try:
                    # e.g. u'0'
                    return str(int(x))
                except (TypeError, ValueError):
                    # look for N/A and N/D plus all sorts of variations
                    text = re.sub('[^A-Z]', '', x.upper())
                    if text == 'NA':
                        return 'N/A'
                    if text == 'ND':
                        return 'N/D'
                    validation_errors.append('Sheet "%s": Expected numeric values in column "%s" (or N/A or N/D), but got text="%s".' % (sheet_name, column_name, x))
                    return 0
        return _inner
    # int type cannot store NaN, so use object type
    for column_name in integer_columns:
        df[column_name] = df[column_name].astype(object).map(validate_int_or_na(column_name))
    # Format any numbers in string columns
    for column_name in string_columns:
        if str(df[column_name].dtype).startswith('float'):
            # an int seems to get detected as float, so convert back to int first
            # or else you get a string like "1.0" instead of "1"
            # e.g. appointments_commission-30-09-2011.xls
            df[column_name] = df[column_name].astype(int)
        df[column_name] = df[column_name].astype(str)
    # Strip strings of spaces
    for column_name in df.columns:
        # columns with strings have detected 'object' type
        if df[column_name].dtype == 'O':
            df[column_name] = df[column_name].str.strip()
    return df


def load_senior(excel_filename, errors, validation_errors, references):
    input_columns = [
      u'Post Unique Reference',
      u'Name',
      u'Grade (or equivalent)',
      u'Job Title',
      u'Job/Team Function',
      u'Parent Department',
      u'Organisation',
      u'Unit',
      u'Contact Phone',
      u'Contact E-mail',
      u'Reports to Senior Post',
      u'Salary Cost of Reports (£)',
      u'FTE',
      u'Actual Pay Floor (£)',
      u'Actual Pay Ceiling (£)',
      u'Total Pay (£)',
      u'Professional/Occupational Group',
      u'Notes',
      u'Valid?']
    rename_columns = {
      u'Total Pay (£)': u'',
      u'Grade': u'Grade (or equivalent)',
    }
    blank_columns = {
      u'Total Pay (£)' : u'',
    }
    integer_columns = [
      u'Actual Pay Floor (£)',
      u'Actual Pay Ceiling (£)',
      u'Salary Cost of Reports (£)',
    ]
    string_columns = [
      u'Post Unique Reference',
      u'Reports to Senior Post',
    ]
    sheet_name = SENIOR_SHEET_NAME
    df = load_excel_store_errors(excel_filename, sheet_name, errors, validation_errors, input_columns, rename_columns, blank_columns, integer_columns, string_columns)
    if df.dtypes['Post Unique Reference']==numpy.float64:
        df['Post Unique Reference'] = df['Post Unique Reference'].astype('int')
    in_sheet_validation(df, validation_errors, sheet_name, 'senior', references)
    return df


def load_junior(excel_filename, errors, validation_errors, references):
    input_columns = [
      u'Parent Department',
      u'Organisation',
      u'Unit',
      u'Reporting Senior Post',
      u'Grade',
      u'Payscale Minimum (£)',
      u'Payscale Maximum (£)',
      u'Generic Job Title',
      u'Number of Posts in FTE',
      u'Professional/Occupational Group',
      u'Valid?']
    integer_columns = [
      u'Payscale Minimum (£)',
      u'Payscale Maximum (£)'
    ]
    string_columns = [
      u'Reporting Senior Post',
    ]
    sheet_name = JUNIOR_SHEET_NAME
    df = load_excel_store_errors(excel_filename, sheet_name, errors, validation_errors, input_columns, {}, [], integer_columns, string_columns)
    if df.dtypes['Reporting Senior Post']==numpy.float64:
        df['Reporting Senior Post'] = df['Reporting Senior Post'].fillna(-1).astype('int')
    in_sheet_validation(df, validation_errors, sheet_name, 'junior', references)
    # 'Valid?'' column doesn't get written in the junior sheet
    df.drop('Valid?', axis=1, inplace=True)
    return df

def diff_lists(a, b):
    a_ = set(a)
    b_ = set(b)
    plus = b_ - a_
    minus = a_ - b_
    output = []
    if plus:
        output.append('+ %s' % ' '.join('"%s"' % p for p in plus))
    if minus:
        output.append('- %s' % ' '.join('"%s"' % m for m in minus))
    return '; '.join(output)


def get_references(xls_filename, errors, validation_errors, warnings):
    references = load_references(xls_filename, errors, validation_errors)
    standard_refs = standard_references()
    if 'listSeniorGrades' in references:
        diff = diff_lists(standard_refs['listSeniorGrades'],
                          references['listSeniorGrades']
                          )
        if diff:
            warnings.append('Mismatch of the senior grades: %s' % diff)
    if 'professions' in references:
        diff = diff_lists(standard_refs['professions'],
                          references['professions']
                          )
        if diff:
            warnings.append('Mismatch of the professions: %s' % diff)
    references.update(standard_refs)
    return references

def standard_references():
    # references in the sheets may be out of date - we could better validate with these latest ones
    references = {}
    references['listSeniorGrades'] = [u'SCS4', u'SCS3', u'SCS2', u'SCS1A', u'SCS1', u'OF-9', u'OF-8', u'OF-7', u'OF-6']
    references['professions'] = [u'Communications', u'Economics', u'Finance', u'Human Resources', u'Information Technology', u'Internal Audit', u'Knowledge and Information Management (KIM)', u'Law', u'Medicine', u'Military', u'Operational Delivery', u'Operational Research', u'Other', u'Planning', u'Policy', u'Procurement', u'Programme and Project Management (PPM)', u'Property and asset management', u'Psychology', u'Science and Engineering', u'Social Research', u'Statisticians', u'Tax Professionals', u'Vets']
    return references

def load_references(xls_filename, errors, validation_errors):
    # Output columns can be different. Update according to the rename_columns dict:
    try:
        dfs = pandas.read_excel(xls_filename,
                                [#'core-24-depts',
                                 '(reference) senior-staff-grades',
                                 '(reference) professions',
                                 '(reference) units',
                                 ])
    except XLRDError, e:
        if str(e) == "No sheet named <'(reference) units'>":
            validation_errors.append(str(e))
            return {}
        elif str(e) in ("No sheet named <'(reference) senior-staff-grades'>",
                      "No sheet named <'(reference) professions'>"):
            # this doesn't matter - we will use the standard_references
            # anyway. Read it again, just for the units.
            try:
                dfs = pandas.read_excel(xls_filename, ['(reference) units'])
            except XLRDError, e:
                if str(e) == "No sheet named <'(reference) units'>":
                    validation_errors.append(str(e))
                else:
                    errors.append(str(e))
                return {}
        else:
            errors.append(str(e))
            return {}
    references = {}
    if '(reference) senior-staff-grades' in dfs:
        references['listSeniorGrades'] = \
            dfs['(reference) senior-staff-grades'].iloc[:, 0].tolist()
    if '(reference) professions' in dfs:
        references['professions'] = \
            dfs['(reference) professions'].iloc[:, 0].tolist()
    references['units'] = \
        dfs['(reference) units'].iloc[:, 0].tolist()
    return references


class MaxDepthError(Exception):
    pass


class PostReportsToUnknownPostError(Exception):
    pass


class PostReportLoopError(Exception):
    pass


JOB_SHARE_COLUMNS_THAT_CAN_BE_DIFFERENT = set((
    'Name', u'Actual Pay Ceiling (£)', u'Actual Pay Floor (£)',
    'Total Pay', 'Contact Phone', 'Contact E-mail', 'Notes', 'FTE'))
SENIOR_SHEET_NAME = '(final data) senior-staff'
JUNIOR_SHEET_NAME = '(final data) junior-staff'

def verify_graph(senior, junior, errors):
    '''Does checks on the senior and junior posts. Writes errors to supplied
    list. Returns None.

    May raise ValidationFatalError if it is so bad that the organogram cannot
    be displayed (e.g. no "top post").
    '''
    # ignore eliminated posts (i.e. don't exist any more)
    senior_ = senior[senior['Name'].astype(unicode) != "Eliminated"]

    # merge posts which are job shares
    # "duplicated will be the grade, job title, job/team function,
    # reports to senior post and salary cost of reports."
    # "post is duplicate save from name, pay columns, contact phone/email and
    #  notes"
    job_share_columns_that_need_to_be_the_same = \
        set(senior_.columns.values) - JOB_SHARE_COLUMNS_THAT_CAN_BE_DIFFERENT
    senior_ = senior_.drop_duplicates(
        keep='first', subset=job_share_columns_that_need_to_be_the_same)
    # detect any remaining duplicate refs
    duplicated_refs = senior_[
        senior_.duplicated(subset=['Post Unique Reference'])
        ]['Post Unique Reference']
    for ref in duplicated_refs:
        if ref in ('XX', 'xx', 0, '0'):
            # it's ok to have several top posts (xx) or
            # posts paid but on leave (0)
            continue
        # rows with that ref, just with the columns that need to be the same
        rows = senior_[senior_['Post Unique Reference']==ref].loc[:,job_share_columns_that_need_to_be_the_same]
        # consider pairs of those rows until we find a problem
        for row_indexes in itertools.combinations(rows.T, 2):
            row_pair = rows.loc[list(row_indexes)]
            columns_with_different_values = \
                row_pair.loc[:,row_pair.iloc[0]!=row_pair.iloc[1]].columns
            error_cols = [column_name(senior.columns.get_loc(col_name))
                         for col_name in columns_with_different_values]
            error_rows = [row_name(index) for index, row in row_pair.iterrows()]
            errors.append('Sheet %s - cells %s%s and %s%s should have the same value. "Post Unique Reference" value "%s" appears in multiple rows, indicating a job share. It is required for job share rows to have identical values in particular columns and that is not the case in this sheet. Rows %s and %s should not have different values for %s.' % (SENIOR_SHEET_NAME, error_cols[0], error_rows[0], error_cols[0], error_rows[1], ref, error_rows[0], error_rows[1], ', '.join(['"%s"' % c for c in columns_with_different_values])))

    # ensure at least one person is marked as top (XX)
    top_persons = senior_[senior_['Reports to Senior Post'].isin(('XX', 'xx'))]
    if len(top_persons) < 1:
        errors.append('Could not find a senior post with "Reports to Senior '
                      'Post" value of "XX" (i.e. the top role)')
        raise ValidationFatalError(errors[-1])
    top_person_refs = top_persons['Post Unique Reference'].values

    # do all seniors report to a correct senior ref? (aside from top person)
    senior_post_refs = set(senior_['Post Unique Reference'])
    senior_report_to_refs = set(senior_['Reports to Senior Post'])
    bad_senior_refs = senior_report_to_refs - senior_post_refs - \
        set(['XX', 'xx'])
    for ref in bad_senior_refs:
        errors.append('Senior post reporting to unknown senior post "%s"'
                      % ref)

    # check there are no orphans in this tree
    reports_to = {}
    refs_that_report_to_themselves = set()
    for index, post in senior_.iterrows():
        ref = post['Post Unique Reference']
        reports_to[ref] = post['Reports to Senior Post']
        if ref == reports_to[ref]:
            errors.append(
                'Sheet "%s" cell %s: Senior post reports to him/herself. '
                'ref:"%s"' %
                (SENIOR_SHEET_NAME, cell_name(index, column_index('k')), ref))
            refs_that_report_to_themselves.add(ref)
    top_level_boss_by_ref = {}

    def get_top_level_boss_recursive(ref, posts_recursed=None):
        if posts_recursed is None:
            posts_recursed = []
        posts_recursed.append(ref)
        if ref in top_person_refs:
            return ref
        if ref in posts_recursed[:-1]:
            raise PostReportLoopError(' '.join(posts_recursed))
        if len(posts_recursed) > 100:
            raise MaxDepthError(' '.join(posts_recursed))
        if ref in top_level_boss_by_ref:
            return top_level_boss_by_ref[ref]
        try:
            boss_ref = reports_to[ref]
        except KeyError:
            known_refs = list(set(reports_to.keys()))
            # convert known_refs to int if poss, so it sorts better
            for i, ref_ in enumerate(known_refs):
                try:
                    known_refs[i] = int(ref_)
                except:
                    pass
            raise PostReportsToUnknownPostError(
                'Post reports to unknown post ref:"%s". '
                'Known post refs:"%s"' %
                (ref, sorted(known_refs)))
        try:
            top_level_boss_by_ref[ref] = get_top_level_boss_recursive(
                boss_ref, posts_recursed)
        except PostReportsToUnknownPostError, e:
            raise PostReportsToUnknownPostError('Error with senior post "%s": %s' % (ref, e))

        return top_level_boss_by_ref[ref]
    for index, post in senior_.iterrows():
        ref = post['Post Unique Reference']
        try:
            top_level_boss = get_top_level_boss_recursive(ref)
        except MaxDepthError, posts_recursed:
            errors.append('Could not follow the reporting structure from '
                          'Senior post %s "%s" up to the top in 100 steps - '
                          'is there a loop? Posts: %s'
                          % (index, ref, posts_recursed))
        except PostReportsToUnknownPostError, e:
            errors.append(str(e))
        except PostReportLoopError, posts_recursed:
            if str(posts_recursed).split(' ')[-1] in \
                    refs_that_report_to_themselves:
                # error has already reported - no point flogging it
                pass
            else:
                errors.append('Reporting structure from Senior post %s "%s" '
                              'ended up in a loop: %s'
                              % (index, ref, posts_recursed))
        else:
            if top_level_boss not in top_person_refs:
                errors.append('Reporting from Senior post %s "%s" up to the '
                              'top results in "%s" rather than "XX"' %
                              (index, ref, top_level_boss))

    # do all juniors report to a correct senior ref?
    junior_report_to_refs = set(junior['Reporting Senior Post'])
    eliminated_posts = set(senior[senior['Name'].astype(unicode) == "Eliminated"]['Post Unique Reference'])
    bad_junior_refs = junior_report_to_refs - senior_post_refs
    for ref in bad_junior_refs:
        if ref in eliminated_posts:
            errors.append('Junior post reporting to Eliminated senior post "%s"'
                          % ref)
        else:
            errors.append('Junior post reporting to unknown senior post "%s"'
                          % ref)

def row_name(row_index):
    '''
    0 returns '2' (first value, after the header row)
    '''
    return row_index + 2

def column_name(column_index):
    '''
    0 returns 'A' (left-most column)
    '''
    return string.ascii_uppercase[column_index]

def column_index(column_name):
    '''
    'A' returns 0
    '''
    return string.ascii_uppercase.index(column_name.upper())

def cell_name(row_index, column_index):
    '''
    (0, 0) returns 'A2' (top-left value, after the header row)
    (12, 2) returns 'B14'
    '''
    return '%s%d' % (column_name(column_index), row_name(row_index))

def in_sheet_validation(df, validation_errors, sheet_name, junior_or_senior, references):
    row_errors = []
    has_valid_column = in_sheet_validation_row_colours(df, row_errors, sheet_name)

    cell_errors = []
    if junior_or_senior == 'senior':
        for index, row in df.iterrows():
            try:
                in_sheet_validation_senior_columns(row, df, cell_errors, sheet_name, references)
            except Exception:
                log.exception('Exception during senior in-sheet validation, row %s' % row.name)
    else:
        for index, row in df.iterrows():
            try:
                in_sheet_validation_junior_columns(row, df, cell_errors, sheet_name, references)
            except Exception:
                log.exception('Exception during junior in-sheet validation, row %s' % row.name)

    if cell_errors and not row_errors and has_valid_column:
        log.error('Errors found by ETL were not picked up by spreadsheet: %r',
                  cell_errors)
        # trust the row_errors (for now) so discard the cell_errors which
        # disagree
        validation_errors.extend(row_errors)
    elif row_errors and not cell_errors:
        log.error('Errors found by spreadsheet were not picked up by ETL: %r',
                  row_errors)
        validation_errors.extend(row_errors)
    else:
        # assume the row_errors are all covered (in more detail) by the
        # cell_errors
        validation_errors.extend(cell_errors)

def in_sheet_validation_senior_columns(row, df, validation_errors, sheet_name, references):
    # senior column A is invalid if:
    # =IF(AND(ISBLANK($B2),ISBLANK($C2),ISBLANK($D2),ISBLANK($E2),ISBLANK($F2),ISBLANK($G2),ISBLANK($H2),ISBLANK($I2),ISBLANK($J2),ISBLANK($K2),ISBLANK($L2),ISBLANK($M2),ISBLANK($N2),ISBLANK($P2),ISBLANK($Q2)),
    #     FALSE,
    #     IF(OR(ISBLANK($A2),ISNUMBER(SEARCH(" ",$A2)),ISNUMBER(SEARCH("XX",$A2)),ISNUMBER(SEARCH("¬",$A2)),ISNUMBER(SEARCH("!",$A2)),ISNUMBER(SEARCH("""",$A2)),ISNUMBER(SEARCH("£",$A2)),ISNUMBER(SEARCH("$",$A2)),ISNUMBER(SEARCH("%",$A2)),ISNUMBER(SEARCH("^",$A2)),ISNUMBER(SEARCH("&",$A2)),ISNUMBER(SEARCH("(",$A2)),ISNUMBER(SEARCH(")",$A2)),ISNUMBER(SEARCH("+",$A2)),ISNUMBER(SEARCH("=",$A2)),ISNUMBER(SEARCH("{",$A2)),ISNUMBER(SEARCH("}",$A2)),ISNUMBER(SEARCH("[",$A2)),ISNUMBER(SEARCH("]",$A2)),ISNUMBER(SEARCH(":",$A2)),ISNUMBER(SEARCH(";",$A2)),ISNUMBER(SEARCH("@",$A2)),ISNUMBER(SEARCH("'",$A2)),ISNUMBER(SEARCH("#",$A2)),ISNUMBER(SEARCH("<",$A2)),ISNUMBER(SEARCH(">",$A2)),ISNUMBER(SEARCH(",",$A2)),ISNUMBER(SEARCH(".",$A2)),ISNUMBER(SEARCH("\",$A2)),ISNUMBER(SEARCH("/",$A2))),
    #        TRUE,FALSE))
    # i.e. valid if the rest of the row is blank
    #      else invalid if it contains a space, XX or any of those symbols
    is_blank_row = not bool(row.iloc[[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16]].any())  # ignore 'O' which is row[14]
    if not is_blank_row:
        a = row[0] or ''
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, 0))
        if 'XX' in a:
            validation_errors.append('%s: You cannot have "XX" in the "Post Unique Reference" column.' % cell_ref)
        elif ' ' in a:
            validation_errors.append('%s: You cannot have spaces in the "Post Unique Reference" column.' % cell_ref)
        elif re.search(r'[¬!\"£$%^&()+=\{\}\[\]:;@\'#<>,.\\/]', a):
            # NB Should we disallow "_" though? The in-sheet validation message says it was allowed...
            validation_errors.append('%s: You cannot have punctuation/symbols in the "Post Unique Reference" column.' % cell_ref)

    # senior column B is invalid if:
    # =NOT(
    #   IF(ISBLANK($A2)
    #      TRUE,
    #      IF(OR($A2="0",$A2=0),
    #         IF($B2="N/D",TRUE,FALSE),
    #         IF(AND($P2>0,OR($B2="N/D",$B2="N/A")),
    #            IF(AND($B2="N/D",OR($P2="N/D",$P2="N/A")),
    #               TRUE,FALSE),
    #            IF(ISBLANK($B2),FALSE,ISTEXT($B2))))))
    a = row.iloc[0]
    b = row.iloc[1]
    p = row.iloc[column_index('P')]
    def is_blank(value):
        return value in (None, '')
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, 1))
        # if A is "0" or 0 then B must be "N/D"
        if a in ('0', 0):
            if b != 'N/D':
                validation_errors.append('%s: Because the "Post Unique Reference" is "0" (individual is paid but not in post) the name must be "N/D".' % cell_ref)
        else:
            try:
                p_is_greater_than_zero_or_a_string = int(p) > 0
            except ValueError:
                # i.e. p is a string
                # =AND('N/D'>0, TRUE)  is TRUE
                p_is_greater_than_zero_or_a_string = True
            if p_is_greater_than_zero_or_a_string and b in ('N/D', 'N/A'):
                # i.e. paid but the name is not disclosed
                # not (b == 'N/D' and p in ('N/D', 'N/A'))  ===
                # b != 'N/D' or p not in ('N/D', 'N/A')
                if b != 'N/D':
                    # i.e. b is N/A
                    validation_errors.append(u'%s: The "Name" cannot be "N/A" (unless "Total Pay (£)" is 0).' % cell_ref)  # unpaid people don't have to be disclosed
                elif p not in ('N/D', 'N/A'):
                    # i.e. p is another string or a positive number (i.e. not 0 or N/D or N/A)
                    validation_errors.append(u'%s: The "Name" cannot be "N/D" unless the "Total Pay (\xa3)" is 0 or N/A or N/D. i.e. Someone whose pay must be disclosed must also have their name disclosed (unless they are unpaid).' % cell_ref)
            elif is_blank(b):
                # we know A is not 0 because then A would require B to be 'N/D'
                validation_errors.append(u'%s: The "Name" cannot be blank.' % cell_ref)

    # senior column C is invalid if:
    # =NOT(IF(ISBLANK($A2),
    #         TRUE,
    #         IF(ISBLANK($C2),
    #            FALSE,
    #            IF(ISNA(MATCH($C2,listSeniorGrades,0)),
    #               FALSE,TRUE))))
    def not_match(value, list_):
        # Excel's MATCH is case insensitive and numbers are the same whether int or strings
        # NB it also allows wildcards ?* and escape char ~ so it would be worth checking
        # there are none of those
        if value == '*' and list_.any():
            return False
        value_ = unicode(value).lower()
        for item in list_:
            if value_ == unicode(item).lower():
                return False
        return True
    c = row.iloc[column_index('C')]
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('C')))
        # invalid if C is blank
        if is_blank(c):
            validation_errors.append(u'%s: The "Grade (or equivalent)" cannot be blank.' % cell_ref)
        else:
            # invalid unless the value is in the listSeniorGrades
            if not_match(c, references['listSeniorGrades']):
                validation_errors.append(u'%s: The "Grade (or equivalent)" must be from the standard list: %s.' % (cell_ref, ', '.join(['"%s"' % grade for grade in references['listSeniorGrades']])))

    # senior column D is invalid if:
    # =NOT(IF(ISBLANK($A2),
    #         TRUE,
    #         IF(ISBLANK($D2),
    #            FALSE,
    #            IF(AND(ISTEXT($D2),$D2<>"N/D"),
    #               IF(OR($A2=0,$A2="0"),
    #                  IF($D2="Not in post",TRUE,FALSE),
    #                  IF($D2="Not in post",FALSE,TRUE)),
    #               FALSE))))
    d = row.iloc[column_index('D')]
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('D')))
        # invalid if D is blank
        if is_blank(d):
            validation_errors.append(u'%s: The "Job Title" cannot be blank.' % cell_ref)
        else:
            if isinstance(d, basestring) and d != 'N/D':
                if a in (0, '0'):
                    if d != 'Not in post':
                        validation_errors.append(u'%s: Because the "Post Unique Reference" is "0" (individual is paid but not in post), the "Job Title" must be "Not in post".' % cell_ref)
                else:
                    if d == 'Not in post':
                        validation_errors.append(u'%s: The "Job Title" can only be "Not in post" if the "Post Unique Reference" is "0" (individual is paid but not in post).' % cell_ref)

    # senior column E is invalid if:
    # =NOT(IF(ISBLANK($A2),
    #         TRUE,
    #         IF(ISBLANK($E2),
    #            FALSE,
    #            IF(AND(ISTEXT($E2),$E2<>"N/D"),
    #               IF($A2=0,
    #                  IF($E2="N/A",TRUE,FALSE),
    #                  IF($E2="N/A",FALSE,TRUE)),
    #               FALSE))))
    e = row.iloc[column_index('E')]
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('E')))
        # invalid if E is blank
        if is_blank(e):
            validation_errors.append(u'%s: The "Job/Team Function" cannot be blank.' % cell_ref)
        else:
            if isinstance(e, basestring) and e != 'N/D':
                if a == 0:  # but what about string '0'?
                    if e != 'N/A':
                        validation_errors.append(u'%s: Because the "Post Unique Reference" is "0" (individual is paid but not in post), the "Job/Team Function" must be "N/A".' % cell_ref)
                else:
                    if e == 'N/A':
                        validation_errors.append(u'%s: The "Job/Team Function" can only be "N/A" if the "Post Unique Reference" is "0" (individual is paid but not in post).' % cell_ref)

    # NB Column F is no longer checked - it became optional with Sept 2016 spreadsheet
    # # senior column F is invalid if:
    # # =NOT(IF(ISBLANK($A2),
    # #         TRUE,
    # #         IF(ISBLANK($F2),
    # #            FALSE,
    # #            IF(ISNA(MATCH($F2,core24,0)),
    # #               FALSE,TRUE))))
    # f = row.iloc[column_index('F')]
    # # valid if A is blank (i.e. as if the row is empty)
    # if not is_blank(a):
    #     cell_ref = 'See sheet "%s" cell %s' % \
    #         (sheet_name, cell_name(row.name, column_index('F')))
    #     # invalid if F is blank
    #     if is_blank(e):
    #         validation_errors.append(u'The "Parent Department" cannot be blank. %s' % cell_ref)
    #     else:
    #         # invalid unless the value is in core24
    #         if not_match(c, references['core24']):
    #             validation_errors.append(u'The "Parent Department" must be from the standard list: %s. %s' % (', '.join(['"%s"' % grade for grade in references['core24']]), cell_ref))

    # senior column G is invalid if:
    # =NOT(IF(ISBLANK($A2),
    #         TRUE,
    #         IF(OR(ISBLANK($G2),$G2="N/D"),
    #            FALSE,TRUE)))
    g = row.iloc[column_index('G')]
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('G')))
        # invalid if G is blank or 'N/D'
        if is_blank(g) or g == 'N/D':
            validation_errors.append(u'%s: The "Organisation" must be disclosed - it cannot be blank or "N/D".' % cell_ref)

    # senior column H is invalid if:
    # =NOT(IF(ISBLANK($A2),
    #         TRUE,
    #         IF(OR(ISBLANK($H2),$H2="N/D"),
    #            FALSE,
    #            IF($A2=0,
    #               IF($H2="N/A",TRUE,FALSE),
    #               IF($H2="N/A",
    #                  FALSE,
    #                  IF(ISNA(MATCH($H2,listUnits,0)),
    #                     FALSE,TRUE))))))
    h = row.iloc[column_index('H')]
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('H')))
        # invalid if H is blank or 'N/D'
        if is_blank(h) or h == 'N/D':
            validation_errors.append(u'%s: The "Unit" must be disclosed - it cannot be blank or "N/D".' % cell_ref)
        else:
            if a == 0:  # but what about string '0'?
                if h != 'N/A':
                    validation_errors.append(u'%s: Because the "Post Unique Reference" is "0" (individual is paid but not in post), the "Unit" must be "N/A".' % cell_ref)
            else:
                if h == 'N/A':
                    validation_errors.append(u'%s: The "Unit" can only be "N/A" if the "Post Unique Reference" is "0" (individual is paid but not in post).' % cell_ref)
                else:
                    # invalid unless the value is in the list of units
                    if not_match(h, references['units']):
                        validation_errors.append(u'%s: The "Unit" must be from the standard list: %s.' % (cell_ref, ', '.join(['"%s"' % grade for grade in references['units']])))

    # senior column I is invalid if:
    # =NOT(IF(ISBLANK($A2),
    #         TRUE,
    #         IF(ISBLANK($I2),
    #            FALSE,
    #            IF(AND(OR(ISNUMBER($I2),ISTEXT($I2)),OR($I2<>"N/D",$J2<>"N/D")),
    #               IF(OR($A2=0,$A2="0",$B2="Vacant",$B2="VACANT",$B2="vacant",$B2="Eliminated",$B2="ELIMINATED",$B2="eliminated"),
    #                  IF($I2="N/A",TRUE,FALSE),
    #                  IF($I2="N/A",FALSE,TRUE)),
    #               FALSE))))
    def is_number(value):
        return isinstance(value, int) or isinstance(value, float)
    i = row.iloc[column_index('I')]
    j = row.iloc[column_index('J')]
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('I')))
        # invalid if I is blank
        if is_blank(i):
            validation_errors.append(u'%s: The "Contact Phone" must be supplied - it cannot be blank.' % cell_ref)
        else:
            if (is_number(i) or isinstance(i, basestring)) and \
                (i != 'N/D' or j != 'N/D'):
                if a in (0, '0') or b in ('Vacant', 'VACANT', 'vacant', 'Eliminated', 'ELIMINATED', 'eliminated'):
                    ref_value = '"Post Unique Reference" is "0" (individual is paid but not in post)' if a in (0, '0') else '"Name" is Vacant" or "Eliminated"'
                    if i != 'N/A':
                        validation_errors.append(u'%s: Because the %s, the "Contact Phone" must be "N/A".' % (cell_ref, ref_value))
                else:
                    if i == 'N/A':
                        validation_errors.append(u'%s: The "Contact Phone" can only be "N/A" if the "Post Unique Reference" is "0" (individual is paid but not in post) or the "Name" is "Vacant".' % cell_ref)
            else:
                # i.e. i = N/D and j = N/D
                validation_errors.append(u'%s: You must provide at least one form of contact. You cannot have both "Contact Phone" and "Contact E-mail" as "N/D".' % cell_ref)

    # senior column J is invalid if:
    # =IF(AND(ISBLANK($A2),ISBLANK($J2)),
    #     FALSE,
    #     IF(AND(OR($A2=0,$A2="0",$B2="Vacant",$B2="VACANT",$B2="vacant",$B2="Eliminated",$B2="ELIMINATED",$B2="eliminated"),
    #            $J2="N/A"),
    #        FALSE,
    #        $AO2))
    # where A02 is: "J invalid?"
    # =IF(AND(ISBLANK($J2),NOT(ISBLANK($A2))),
    #     TRUE,
    #     IF(AND($J2="N/A",$A2<>"0"),
    #        TRUE,
    #        IF(AND($I2="N/D",$J2="N/D"),
    #           TRUE,
    #           IF(OR($J2="N/D",
    #                 AND(ISTEXT($J2),
    #                     ISNUMBER(SEARCH("@",$J2)),
    #                     ISNUMBER(SEARCH(".",$J2))
    #                     )
    #                 ),
    #              FALSE,TRUE))))

    # valid if A and J are blank. If either has a value, we continue the logic.
    if not (is_blank(a) and is_blank(j)):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('J')))
        if (a in (0, '0') or b in ('Vacant', 'VACANT', 'vacant', 'Eliminated', 'ELIMINATED', 'eliminated')) and \
            j == 'N/A':
            pass  # valid
        else:
            # invalid if ao2 is True
            # j_invalid = (is_blank(j) and not is_blank(a)) or \
            #     (j == 'N/A' and a != '0') or \
            #     (i == 'N/D' and j == 'N/D') or \
            #     not (j == 'N/D' or (isinstance(j, basestring) and
            #                         '@' in j and '.' in j))
            # split up ao2 into the four conditions
            if is_blank(j) and not is_blank(a):
                validation_errors.append(u'%s: The "Contact E-mail" must be supplied - it cannot be blank.' % cell_ref)
            elif j == 'N/A' and a != '0':  # what about a = int 0!
                validation_errors.append(u'%s: The "Contact E-mail" can only be "N/A" if the "Post Unique Reference" is "0" (individual is paid but not in post).' % cell_ref)
            elif i == 'N/D' and j == 'N/D':
                validation_errors.append(u'%s: You must provide at least one form of contact. You cannot have both "Contact Phone" and "Contact E-mail" as "N/D".' % cell_ref)
            elif not (j == 'N/D' or (isinstance(j, basestring) and
                                     '@' in j and '.' in j)):
                validation_errors.append(u'%s: The "Contact E-mail" must be a valid email address (containing "@" and "." characters) unless the "Name" is "Vacant" or "Eliminated", or the "Post Unique Reference" is "0" (the individual is paid but not in post). It cannot be blank.' % cell_ref)

    # senior column K is invalid if:
    # =NOT(IF(ISBLANK($A2),
    #         TRUE,
    #         IF(ISBLANK($K2),
    #            FALSE,
    #            IF($K2="XX",
    #               TRUE,
    #               IF(ISNA(MATCH($K2,seniorPostUniqueReference,0)),
    #                  FALSE,TRUE)))))
    # where: seniorPostUniqueReference is a formula:
    #          ='(final data) senior-staff'!$A$2:$A$2000
    k = row.iloc[column_index('K')]
    # valid if A is blank (i.e. as if the row is empty)
    if not is_blank(a):
        cell_ref = 'Sheet "%s" cell %s' % \
            (sheet_name, cell_name(row.name, column_index('K')))
        # invalid if K is blank
        if is_blank(k):
            validation_errors.append(u'%s: The "Reports to Senior Post" value must be supplied - it cannot be blank.' % cell_ref)
        else:
            if k != 'XX':  # what about lowercase?
                seniorPostUniqueReference = df.ix[:, 0]
                # invalid unless the value is in column A
                if not_match(k, seniorPostUniqueReference):
                    validation_errors.append(u'%s: The "Reports to Senior Post" value must match one of the values in "Post Unique Reference" (column A) or be "XX" (which is a top level post - reports to no-one in this sheet).' % cell_ref)

def in_sheet_validation_junior_columns(row, df, validation_errors, sheet_name, references):
    # to do
    pass


def in_sheet_validation_row_colours(df, validation_errors, sheet_name):
    '''
    returns: success of finding a colour/value in the Valid? column
    '''
    # Row validation indication
    validation_column = df.columns.get_loc('Valid?') # equivalent to S
    if len(df) and len(df[df['Valid?'].notnull()]) == 0:
        # there is no in-sheet validation - probably because it was generated
        # from the triplestore
        return False
    rows_marked_invalid = df[df['Valid?'] == 0]
    if len(rows_marked_invalid):
        row = rows_marked_invalid.head(1)
        row_index = row.index[0]
        err = 'Sheet "%s" has %d invalid row%s. The %sproblem is on row %d, as indicated by the red colour in cell %s.' % (sheet_name, len(rows_marked_invalid), 's' if len(rows_marked_invalid) > 1 else '', 'first ' if len(rows_marked_invalid) > 1 else '', row_name(row_index), cell_name(row_index, validation_column))
        validation_errors.append(err)
    return True

def get_date_from_filename(filename):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename) or \
        re.search(r'(\d{2}-\d{2}-\d{4})', filename)
    assert match, 'Cannot find date in filename: %s' % filename
    return match.groups()[0]


def get_verify_level(graph):
    # parse graph date
    graph_match = re.match(
        r'^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$',
        graph) or \
        re.match(
        r'^(?P<day>\d{2})-(?P<month>\d{2})-(?P<year>\d{4})$',
        graph)
    assert graph_match, \
        'Could not parse graph YYYY-MM-DD / DD-MM-YYYY: %r' % graph
    graph = graph_match.groupdict()
    graph['year'] = int(graph['year'])
    graph['month'] = int(graph['month'])

    # verify level based on the date
    if graph['year'] == 2011:
        # Be very lenient - overlook all errors for these early 2011 ones
        # because the data clearly wasn't validated at this time:
        # * some posts are orphaned
        # * some posts report to posts which don't exist
        # * some post reporting loops (including roles reporting to himself)
        # * some job-shares are people of different grades so you get errors
        #   about duplicate post refs.
        return 'load'
    elif graph['year'] <= 2015 or \
            (graph['year'] == 2016 and graph['month'] == 3):
        # Be quite lenient. During 2012 - 2016/03 TSO did only basic validation
        # and we see errors:
        # * 'Senior post "Post Unique Reference" is not unique'
        # * u'Expected numeric values in column "Actual Pay '
        # * 'Senior post reports to him/herself.'
        # * 'Senior post reporting to unknown senior post'
        # * 'Junior post reporting to unknown senior post'
        # * 'ended up in a loop'
        # * 'Post reports to unknown post'
        return 'load and display'
    else:
        # Drupal-based workflow actually displays the problems to the user, so
        # we can enforce all errors
        return 'load, display and be valid'


def load_xls_and_get_errors(xls_filename):
    '''
    Used by tso_combined.py
    Does all checks and returns all errors.
    Returns: (senior_df, junior_df, errors, warnings, will_display)
    '''
    load_errors = []
    validation_errors = []
    warnings = []
    references = get_references(xls_filename, load_errors, validation_errors, warnings)
    senior_df = load_senior(xls_filename, load_errors, validation_errors, references)
    junior_df = load_junior(xls_filename, load_errors, validation_errors, references)

    if load_errors:
        return None, None, load_errors + validation_errors, warnings, False

    errors = validation_errors
    try:
        verify_graph(senior_df, junior_df, errors)
    except ValidationFatalError, e:
        # display error - organogram is not displayable
        return None, None, [unicode(e)], warnings, False

    # If we get this far then it will display, although there might be problems
    # with some posts
    errors = dedupe_list(errors)
    return senior_df, junior_df, errors, warnings, True


def print_error(error_msg):
    print 'ERROR:', error_msg.encode('utf8')  # encoding for Drupal exec()


def load_xls_and_stop_on_errors(xls_filename, verify_level, print_errors=True):
    '''
    Loads the XLS, verifies it to an appropriate level and returns the data.

    If errors are not acceptable, it prints them and returns None.
    Returns: failure_stage, senior_df, junior_df, errors, warnings
    '''
    load_errors = []
    validation_errors = []
    warnings = []
    references = get_references(xls_filename, load_errors, validation_errors, warnings)
    senior_df = load_senior(xls_filename, load_errors, validation_errors, references)
    junior_df = load_junior(xls_filename, load_errors, validation_errors, references)

    if load_errors:
        print 'Critical error(s):'
        if print_errors:
            for error in load_errors:
                print_error(error)
        # errors mean no rows can be got from the file, so can't do anything
        return 'load', senior_df, junior_df, load_errors, warnings
    if validation_errors and verify_level == 'load, display and be valid':
        print 'Validation error(s) during load:'
        if print_errors:
            for error in validation_errors:
                print_error(error)
        return 'validation', senior_df, junior_df, validation_errors, warnings

    validate_errors = []
    if verify_level != 'load':
        try:
            verify_graph(senior_df, junior_df, validate_errors)
        except ValidationFatalError, e:
            # display error - organogram is not displayable
            if print_errors:
                print_error(unicode(e))
            return 'validating tree', senior_df, junior_df, validate_errors, warnings

        if verify_level == 'load, display and be valid' and validate_errors:
           validate_errors = dedupe_list(validate_errors)
           if print_errors:
                for error in validate_errors:
                    print_error(error)
           return 'validating tree', senior_df, junior_df, validate_errors, warnings
    return None, senior_df, junior_df, validate_errors, warnings


def dedupe_list(things):
    seen = set()
    seen_add = seen.add
    return [x for x in things if not (x in seen or seen_add(x))]


def main(input_xls_filepath, output_folder):
    print "Loading", input_xls_filepath

    if args.date:
        verify_level = get_verify_level(args.date)
    elif args.date_from_filename:
        date_ = get_date_from_filename(input_xls_filepath)
        verify_level = get_verify_level(date_)
    else:
        verify_level = 'load, display and be valid'
    failure_stage, senior_df, junior_df, errors, warnings = \
        load_xls_and_stop_on_errors(input_xls_filepath, verify_level,
                                    print_errors=True)
    if failure_stage != None:
        # fatal error has been printed
        return

    # Calculate Organogram name
    _org = senior_df['Organisation']
    _org = _org[_org.notnull()].unique()
    name = " & ".join(_org)
    if name == u'Ministry of Defence':
        _unit = senior_df['Unit']
        _unit = _unit[_unit.notnull()].unique()
        name += " - " + (" & ".join(_unit))
    # Write output files
    basename, extension = os.path.splitext(os.path.basename(input_xls_filepath))
    senior_filename = os.path.join(output_folder, basename + '-senior.csv')
    junior_filename = os.path.join(output_folder, basename + '-junior.csv')
    print "Writing", senior_filename, junior_filename

    save_csvs(senior_filename, junior_filename, senior_df, junior_df)

    # Write index file - used by Drupal
    index = [{'name': name, 'value': basename}]  # a list because of legacy
    index = sorted(index, key=lambda x: x['name'])
    index_filename = os.path.join(output_folder, 'index.json')
    print "Writing index file:", index_filename
    with open(index_filename, 'w') as f:
        json.dump(index, f)
    print "Done."
    # return values are only for the tests
    return senior_filename, junior_filename, senior_df, junior_df

def save_csvs(senior_filename, junior_filename, senior_df, junior_df):
    csv_options = dict(encoding="utf-8",
                       quoting=csv.QUOTE_ALL,
                       float_format='%.2f',
                       index=False)
    senior_df.to_csv(senior_filename, **csv_options)
    junior_df.to_csv(junior_filename, **csv_options)


def usage():
    print "Usage: %s input_1.xls input_2.xls ... output_folder/" % sys.argv[0]
    sys.exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',
                        help='The strength of verify level picked according '
                             'to the date of the data (YYYY-MM-DD)')
    parser.add_argument('--date-from-filename',
                        action='store_true',
                        help='The strength of verify level picked according '
                             'to the date of the data, extracted from the '
                             'filename (for manual tests only!)')
    parser.add_argument('input_xls_filepath')
    parser.add_argument('output_folder')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()
    if not os.path.isdir(args.output_folder):
        parser.error("Error: Not a directory: %s" % args.output_folder)
    if not os.path.exists(args.input_xls_filepath):
        parser.error("Error: File not found: %s" % args.input_xls_filepath)
    if args.verbose:
        logging.basicConfig()
    else:
        logging.basicConfig(level=logging.CRITICAL)
    main(args.input_xls_filepath, args.output_folder)
