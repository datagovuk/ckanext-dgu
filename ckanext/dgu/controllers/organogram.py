import datetime
import os.path
import logging

from pylons import config

from ckan.lib.base import h, BaseController, abort
from ckanext.dgu.plugins_toolkit import (
    render, c, request, _,
    ValidationError, get_action, check_access)
from ckanext.dgu.bin.organograms_etl_to_csv import load_xls_and_get_errors, \
    save_csvs, get_verify_level
import ckan.plugins as p
from ckanext.dgu.lib import helpers as dgu_helpers
from ckanext.dgu.model.organogram import Organogram
import ckanext.dgu.lib.inventory as inventory_lib
from ckan.model.types import make_uuid

log = logging.getLogger(__name__)


class DguOrganogramController(BaseController):
    def home(self):
        pass

    def publication_index(self):
        publishers = dgu_helpers.organogram_permissions_for_current_user()
        return render('organogram/publication_index.html',
                      extra_vars=dict(publishers=publishers))

    def publication(self, org_name):
        from ckan import model
        if not c.user:
            abort(401, 'You need to log-in to see this page')
        publishers = dgu_helpers.organogram_permissions_for_current_user()
        if org_name not in [pub.name for pub in publishers]:
            abort(401, 'You do not have permission for this publisher')
        organization = model.Group.get(org_name)
        if not organization:
            abort(404, 'Organization not found')
        rows = get_rows(organization)
        today = datetime.datetime.now()

        return render('organogram/publication.html',
                      extra_vars=dict(publishers=publishers,
                                      publisher=organization,
                                      today=today,
                                      rows=rows[::-1],
                                      ))

    def upload(self, org_name, date):
        from ckan import model

        # user permissions
        if not c.user:
            abort(401, 'You need to log-in to see this page')
        publishers = dgu_helpers.organogram_permissions_for_current_user()
        if org_name not in [pub.name for pub in publishers]:
            abort(401, 'You do not have permission for this publisher')
        organization = model.Group.get(org_name)
        if not organization:
            abort(404, 'Organization not found')

        # check there is still a free slot for this file
        rows = get_rows(organization)
        date_str = date
        try:
            date = datetime.datetime.strptime(date, '%d-%m-%Y')
        except ValueError:
            abort(400, 'Date format error')
        for row in rows:
            if row['version'] == date:
                break
        else:
            abort(400, 'Date not found')
        if row['organogram']:
            abort(400, 'There is an organogram already for that date')

        if request.method == 'POST':
            # receive the file
            # field storage:
            # If a field represents an uploaded file, accessing the value via
            # the value attribute or the getvalue() method reads the entire
            # file in memory as a string. This may not be what you want. You
            # can test for an uploaded file by testing either the filename
            # attribute or the file attribute. You can then read the data at
            # leisure from the file attribute
            if 'upload' not in request.POST or \
                    not hasattr(request.POST['upload'], "filename"):
                h.flash_error('No file was selected. Please choose a file '
                              'before uploading')
                # redirect to get the flash message displayed
                return p.toolkit.redirect_to(
                    controller=''
                    'ckanext.dgu.controllers.organogram:InventoryController',
                    action='upload', org_name=org_name, date=date_str)

            # move the file out of the cgi.FieldStorage file into a temp file
            incoming = request.POST['upload'].filename
            file_root = config.get('dgu.organogram.temporary-storage', '/tmp')
            filepath = os.path.join(
                file_root, make_uuid()) + "-{0}".format(incoming)
            # Ensure the directory exists. The uploaded filename may
            # contain a path(?)
            directory = os.path.dirname(filepath)
            if not os.path.exists(directory):
                os.makedirs(directory)

            with inventory_lib.UploadFileHelper(
                    incoming, request.POST['upload'].file) as f:
                open(filepath, 'wb').write(f.read())

            # Run validation
            system_errors, failure_stage, validation_errors, warnings = \
                validate_and_save(filepath, organization, date)

            # Show results
            if system_errors:
                msg = '<strong>Failure</strong><br>'\
                    'There was a system error during reading the uploaded '\
                    'file. The administrators have been '\
                    'alerted. For further help email: team@data.gov.uk using'\
                    ' subject "Organograms"'
                return p.toolkit.redirect_to(
                    controller=''
                    'ckanext.dgu.controllers.organogram:InventoryController',
                    action='upload', org_name=org_name, date=date_str)
            elif validation_errors:
                msg = '<strong>Failure during %s</strong><br>'\
                    'The file had error(s) which must be resolved before it '\
                    'can be accepted:<br><br>' % failure_stage
                msg += '<br><br>'.join(['* %s' % e for e in validation_errors])
                msg += '<br>NB that a few more consistency checks are being '\
                    'carried out and more detailed error messages provided to'\
                    ' help resolve them.'
                msg += '<br>For further help email: team@data.gov.uk using'\
                    ' subject "Organograms"'
                if warnings:
                    msg += '<br><br>In addition there are some warnings, '\
                        'purely for your information:<br><br>'
                    msg += '<br><br>'.join(['* %s' % e for e in warnings])
                h.flash_error(msg, html_allowed=True)
                return p.toolkit.redirect_to(
                    controller=''
                    'ckanext.dgu.controllers.organogram:InventoryController',
                    action='upload', org_name=org_name, date=date)
            msg = '<strong>Success</strong> '\
                'This organogram has been accepted for %s' % date
            if warnings:
                msg += '<br><br>In addition there are some warnings, '\
                    'purely for your information:<br><br>'
                msg += '<br><br>'.join(['* %s' % e for e in warnings])
            h.flash_error(msg, html_allowed=True)

            return p.toolkit.redirect_to(
                controller=''
                'ckanext.dgu.controllers.organogram:InventoryController',
                action='publication', org_name=org_name)
        else:
            # show the form
            return render('organogram/upload.html',
                          extra_vars=dict(date=date,
                                          publisher=organization))

def validate_and_save(source_xls_filepath, organization, date):
    '''Returns:
        system_errors, failure_stage, errors, warnings
    '''
    try:
        verify_level = get_verify_level(date)

        # Extract and Transform
        failure_stage, senior_df, junior_df, errors, warnings = \
            load_xls_and_stop_on_errors(source_xls_filepath, verify_level,
                                        print_errors=False)
        if failure_stage:
            return None, failure_stage, errors, warnings

        # Prepare to save to db
        organogram_dict = dict(
            publisher_id=organization.id,
            date=date,
            upload_user=c.user_obj.id,
            upload_date=datetime.datetime.now(),
            signoff_user=None,
            signoff_date=None,
            publish_user=None,
            publish_date=None,
            state='uploaded',
            )

        # Save to CSV
        csv_rel_filepaths = []
        for senior_or_junior in ('senior', 'junior'):
            out_filename = '{org}-{graph}-{senior_or_junior}.csv'.format(
                org=munge_org(org.title, separation_char='_'),
                graph=graph.replace('/', '-'),
                senior_or_junior=senior_or_junior)
            check_filename_is_unique(
                get_csv_filepath(out_filename, relative=True),
                'csv_%s_filepath' % senior_or_junior,
                organogram_dict, stats)
            csv_rel_filepaths.append(get_csv_filepath(out_filename,
                                                      relative=True))
        senior_csv_rel_filepath, junior_csv_rel_filepath = csv_rel_filepaths
        senior_csv_filepath, junior_csv_filepath = \
            [full_path(rel_path) for rel_path in csv_rel_filepaths]

        save_csvs(senior_csv_filepath, junior_csv_filepath,
                  senior_df, junior_df)
        organogram_dict['csv_senior_filepath'] = senior_csv_rel_filepath
        organogram_dict['csv_junior_filepath'] = junior_csv_rel_filepath

        # copy the XLS file into the organogram dir
        if row['original_xls_filepath']:
            xls_filename = munge_xls_path(row['original_xls_filepath'])
        else:
            xls_filename = 'from-triplestore-' + row['xls_path'].split('/')[-1]
        xls_rel_filepath = get_xls_filepath(xls_filename, relative=True)
        check_filename_is_unique(xls_rel_filepath, 'xls_filepath',
                                 organogram_dict, stats)
        xls_filepath = full_path(xls_rel_filepath)
        if os.path.exists(xls_filepath):
            os.remove(xls_filepath)
        shutil.copyfile(source_xls_filepath, xls_filepath)
        organogram_dict['xls_filepath'] = xls_rel_filepath

        # save to the database
        if existing_organogram:
            existing_organogram.update(**organogram_dict)
        else:
            organogram = Organogram(**organogram_dict)
            model.Session.add(organogram)
        model.Session.commit()
        # success
        return None, None, None, None
    except:
        user = c.user
        if c.user_obj:
            user += ' "%s" %s' % c.user_obj.fullname, c.user_obj.email
        log.error('Exception during organogram upload validation & saving: '
                  '%s %s %s %s', source_xls_filepath, organization.name,
                  date.strftime('%d-%m-%Y'), user)
        log.exception('upload')
        return True, None, None, None

def get_rows(organization):
    rows = []
    today = datetime.datetime.now()
    version_first_of_month = datetime.datetime(2011, 3, 1)
    while True:
        version = last_day_of_same_month(version_first_of_month)
        previous_version = six_months_previous(version)
        due = get_due_date(version)
        previous_version_due = get_due_date(previous_version)
        if today < previous_version_due:
            break
        if today > due:
            status_if_not_published = 'Outstanding'
        elif previous_version_due < today <= due:
            status_if_not_published = 'Due by %s' % due.strftime('%d/%m/%Y')
        else:
            status_if_not_published = 'Due next'
        organogram = Organogram.get(publisher_id=organization.id, date=version)
        rows.append(dict(
            version=version,
            status_if_not_published=status_if_not_published,
            due=due,
            previous_version_due=previous_version_due,
            organogram=organogram,
            ))
        version_first_of_month = last_day_of_same_month(
            six_months_on(version_first_of_month))
    return rows

days_in_months = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

def six_months_previous(date):
    new_month = (date.month - 6) % 12
    days_in_month = days_in_months[new_month - 1]
    day = date.day if date.day <= days_in_month else days_in_month
    return datetime.datetime(
        date.year + (date.month - 6) / 12,
        new_month,
        day)

def six_months_on(date):
    new_month = (date.month + 6) % 12
    days_in_month = days_in_months[new_month - 1]
    day = date.day if date.day <= days_in_month else days_in_month
    return datetime.datetime(
        date.year + (date.month + 6) / 12,
        new_month,
        day)

def last_day_of_same_month(first_day_of_month):
    return datetime.datetime(
        first_day_of_month.year,
        first_day_of_month.month + 1,
        1) - \
        datetime.timedelta(days=1)

def get_due_date(version):
    return datetime.datetime(
        version.year,
        6 if version.month == 3 else 12,
        6)