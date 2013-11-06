"""
Celery tasks for processing inventory uploads.

When a user uploads an inventory spreadsheet, it is submitted to a celery
queue and processed here.
"""
import datetime
import json
import os
import requests
import urlparse
import traceback

import messytables

from ckan.lib.celery_app import celery
import ckan.lib.munge as munge
from ckan.lib.field_types import DateType, DateConvertError
from ckanclient import CkanClient, CkanApiError

def _process_upload(context, data):
    """
    When provided with a filename this function will process each row
    within the file and then return a tuple. The tuple will contain
        - a list of error messages (if any)
        - a list of dicts where each dict contains ...
                {
                 'package': 'a_package_id',
                 'action':  'Added' or 'Updated'
                }
    """
    log = inventory_upload.get_logger()

    errors = []
    results = []

    filename = data['file']
    publisher_name = data['publisher']

    import urlparse
    client = CkanClient(base_location=urlparse.urljoin(context['site_url'],'api'),
                        api_key=context['apikey'])

    tableset = None
    try:
        _, ext = os.path.splitext( filename )
        tableset = messytables.any_tableset(open(filename, 'r'), extension=ext[1:])
    except Exception, e:
        if str(e) == "Unrecognized MIME type: text/plain":
            tableset = messytables.any_tableset(f, mimetype="text/csv")
        else:
            errors.append("Unable to load file: {0}".format(e))

    if not tableset:
        errors.append("Unable to read data from uploaded file. Please contact a sysadmin.")
        return errors, results

    first = True
    pos = 0
    for row in tableset.tables[0]:
        pos = pos + 1
        if first:
            # Validate the header row to make sure it hasn't been modified
            ok, msg = validate_incoming_inventory_header(row)
            if not ok:
                errors.append(msg)
                break
            first = False
            continue

        try:
            pkg, msg = \
                process_incoming_inventory_row(pos, row, publisher_name, client, log)
            if pkg:
                results.append({'package': pkg['id'], 'action': msg})
        except Exception, exc:
            row_identity = str(pos)
            try:
                row_identity += ' (%s)' % row[0].value
            except:
                pass
            errors.append('Row %s: %s' % (row_identity, str(exc)))

    if pos < 2 and len(errors) == 0:
        errors.append("There was not enough data in the upload file")

    return errors, results


def upload_inventory_file(context, data):
    """

    """
    log = inventory_upload.get_logger()
    now = datetime.datetime.now().isoformat()

    log.info(data)
    errors, results = _process_upload(context, data)
    if not errors:
        try:
            os.unlink(data['file'])
        except:
            pass

    data = {
            'entity_id': data['jobid'],
            'entity_type': u'inventory',
            'task_type': 'inventory.upload',
            'key': u'status',
            'value': json.dumps(results),
            'state': 'Complete',
            'error': json.dumps(errors),
            'last_updated': now
        }
    log.info(data)
    update_task_status(context, data, log)
    return json.dumps(results),


def update_task_status(context, data, log):
    """
    Use CKAN API to update the task status.

    Params:
      context - dict containing 'site_url', 'site_user_apikey'
      data - dict representing one row in the task_status table:
               entity_id, entity_type, task_type, key, value,
               error, stack, last_updated

    May raise CkanError if the request fails.

    Returns the content of the response.
    """
    api_url = urlparse.urljoin(context['site_url'], 'api/action') + '/task_status_update'
    post_data = json.dumps(data)
    res = requests.post(
        api_url, post_data,
        headers = {'Authorization': context['site_user_apikey'],
                   'Content-type': 'application/json'}
    )
    if res.status_code == 200:
        log.info('Task status updated OK')
        return res.content
    else:
        try:
            content = res.content
        except:
            content = '<could not read request content to discover error>'
        log.error('ckan failed to update task_status, status_code (%s), error %s. Maybe the API key or site URL are wrong?.\ncontext: %r\ndata: %r\nres: %r\nres.error: %r\npost_data: %r\napi_url: %r'
                        % (res.status_code, content, context, data, res, res.error, post_data, api_url))
        raise CkanApiError('ckan failed to update task_status, status_code (%s), error %s'  % (res.status_code, content))
    log.info('Task status updated ok: %s=%s', key, value)


@celery.task(name = "inventory.process")
def inventory_upload(context, data):
    '''
    Processes an uploaded file
    Params:
        context = {
            'username': user.name,
            'site_url': config.get('ckan.site_url_internally') or config.get('ckan.site_url'),
            'apikey': user.apikey,
            'site_user_apikey': site_user['apikey']
        }
        data = {
            'file': filename,
            'publisher': publisher.name,
        }
    '''
    log = inventory_upload.get_logger()
    log.info('Starting inventory upload task: %r', data)
    try:
        data = json.loads(data)
        context = json.loads(context)
        result = upload_inventory_file(context, data)
        return result
    except Exception, e:
        # Any problem at all is recorded in task_status and then reraised
        log.error('Error occurred during inventory upload: {0}'.format(e))
        update_task_status(context, {
            'entity_id': data['jobid'],
            'entity_type': u'inventory',
            'task_type': 'inventory.upload',
            'key': u'celery_task_id',
            'value': unicode(inventory_upload.request.id),
            'error': '%s: %s' % (e.__class__.__name__,  unicode(e)),
            'stack': traceback.format_exc(),
            'last_updated': datetime.datetime.now().isoformat()
        }, log)
        raise


def validate_incoming_inventory_header(header_row):
    """
    Simple validation of the header row to make sure we have the 4 headers we
    expect in the right place.
    """
    if len(header_row) < 5:
        return False, "There are not enough columns in the spreadsheet."

    if header_row[0].value.strip() != 'Title' or \
            header_row[1].value.strip() != 'Description' or \
            header_row[2].value.strip() != 'Owner':
        return False, "Header row titles have been changed"

    return True, ""

def process_incoming_inventory_row(row_number, row, default_group_name, client, log):
    """
    Reads the provided row and updates the information found in the
    database where appropriate.

    The text of any exception raised will be shown to the user and the
    processing aborted.
    """
    try:
        title = row[0].value.encode('utf-8')
    except Exception, e:
        raise Exception('Error with encoding of Title: %s' % e)
    try:
        description = row[1].value.encode('utf-8')
    except Exception, e:
        raise Exception('Error with encoding of Description: %s' % e)
    publisher_name = row[2].value
    publish_date = row[3].value
    release_notes = row[4].value

    if isinstance(publish_date, basestring) and publish_date.strip():
        # e.g. CSV containing "1/2/14" -> "14/02/01"
        try:
            publish_date = DateType.form_to_db(publish_date)
        except DateConvertError:
            # Lots of text went into this field but have decided to not allow from now
            # and it never gets displayed.
            msg = 'Could not parse date: "%s" Must be: DD/MM/YY' % publish_date
            log.error(msg)
            raise Exception(msg)
    if isinstance(publish_date, datetime.datetime):
        # e.g. Excel -> "14/02/01"
        publish_date = DateType.date_to_db(publish_date)
    if not isinstance(publish_date, basestring):
        # e.g. Excel int
        msg = 'Could not parse date: "%s" Must be: DD/MM/YY' % publish_date
        log.error(msg)
        raise Exception(msg)

    group = None
    if publisher_name:
        try:
            result = client.action('group_search', query=publisher_name, exact=True)
            if result['count'] == 0:
                group = None
                raise Exception('Publisher does not exist in data.gov.uk: "%s"' % publisher_name)
            else:
                group = result['results'][0]
        except Exception, e:
            log.exception('System error on group_search: %s', e)
            raise Exception('System error checking publisher: %s' % e)

    # First validation check, make sure we have enough to either update or create an
    # unpublished item
    missing_fields = []
    if not title.strip():
        missing_fields.append("Dataset title")

    if not description.strip():
        missing_fields.append("Description of dataset")

    if not group:
        missing_fields.append("Owner")

    if missing_fields:
        raise Exception("The following fields were missing: {1}".format(", ".join(missing_fields)))

    # Check if we can find the dataset by title (for inventory items)
    # If this happens it's kinda hard to work out which we want.  The group might be different
    # to the one that the user just sent us, it might be that it belongs to someone else.
    possibles = []
    existing_pkg = None
    log.info(title)

    try:
        results = client.package_search('',{'title':title})
    except Exception, e:
        log.error(e)
        raise Exception("There was an error looking for existing datasets")

    log.info("Title lookup found {0} results".format(results['count']))
    for pname in results['results']:
        possible_pkg = _get_package(client, pname)
        if not possible_pkg:
            continue

        try:
            encoded_title = possible_pkg['title'].lower().encode('utf-8')
        except Exception, e:
            raise Exception('Error with encoding of Title for package name %s: %s' % (pname, e))
        if not encoded_title == title.lower():
            log.info("{0} does not match title {1}".format(encoded_title, title) )
            continue

        if not possible_pkg['extras'].get('unpublished', False):
            # If the title has matched exactly, and the thing we matched isn't an
            # unpublished item, we should alert the user to the existing of the dataset
            raise Exception("The non-inventory dataset '{0}' already exists".format(title))

        if group['name'] != possible_pkg.get('organization', {}).get('name'):
            log.info("Group name {0} does not match this possible packages organization in {1}".format(group['name'],possible_pkg['organization']))
            continue

        log.info("Adding {0} as possible package".format(possible_pkg['name']))
        possibles.append(possible_pkg)

    log.info("There are {0} possible matches".format(len(possibles)))

    # If we can edit only one of them, then we should do that.
    existing_pkg = None
    if len(possibles) == 1:
        existing_pkg = possibles[0]
    elif len(possibles) > 1:
        raise Exception("Found {0} existing unpublished items with title '{1}'".format(len(possibles), title))

    log.debug("Existing package? {0}".format(not existing_pkg is None))
    if existing_pkg:
        existing_pkg['extras']['release-notes'] = release_notes
        existing_pkg['extras']['publish-date'] = publish_date
        existing_pkg['notes'] = description or pkg.notes

        client.package_entity_put(existing_pkg)

        return (existing_pkg, "Updated",)

    log.info("Creating new dataset: {0}".format(title))
    # Looks like a new unpublished item, so we'll create a new one.

    def get_clean_name(s):
        current = s
        counter = 1
        while True:
            current = munge.munge_title_to_name(current)
            if not _get_package(client, current):
                break
            current = "{0}_{1}".format(s, counter)
            counter = counter + 1
        return current

    package = {}
    package["title"] = title
    package["name"] = get_clean_name(title)
    package["notes"] = description or " "
    package["access_constraints"] = ""
    package["api_version"] = "3"
    package['license_id']  = "unpublished"
    package['foi-name'] = ""
    package['foi-email'] = ""
    package['foi-web'] = ""
    package['foi-phone'] = ""
    package['contact-email'] = ""
    package['contact-phone'] = ""
    package['contact-name'] = ""
    package['theme-primary'] = ""

    package['owner_org'] = group['name']

    # Setup unublished specific items
    extras = {
        'unpublished': True,
        'publish-date': publish_date,
        'release-notes':release_notes
    }
    package['extras'] = extras

    log.info("Creating new unpublished package: {0}".format(package['name']))

    try:
        package = client.package_register_post(package)
    except Exception, e:
        log.error(e)
        raise Exception("There was a problem saving '{0}'".format(title))

    return (package, "Added",)

def _get_package(client, pkg_name):
    try:
        pkg = client.package_entity_get(pkg_name)
    except CkanApiError, e:
        if client.last_status == 404:
            pkg = None
        else:
            raise Exception('Unexpected status %s checking for package under \'%s\': %r' % (client.last_status, pkg_name, e.args))
    return pkg
