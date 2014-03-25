import os
import datetime
import json
import ckan.lib.munge as munge
from ckanext.dgu.plugins_toolkit import (c, NotAuthorized,
    ValidationError, get_action, check_access)
from ckan.lib.search import SearchIndexError

def inventory_dumper(tmpfile, query):
    """ Dumps all of the inventory items to the open tmpfile using the
        packages provided by query """
    import csv
    import dateutil.parser

    writer = csv.writer(tmpfile)
    writer.writerow(["Name", "Description", "Department", "Publish date", "Release notes"])
    for pkg in query.all():
        if not pkg.extras.get('unpublished', False):
            continue

        org = pkg.get_organization()
        if not org:
            # This should not happen, but does appear in test data during development
            grp = 'Unknown'
        else:
            grp = org.title


        publish_date = pkg.extras.get('publish-date', '')
        if publish_date:
            try:
                dt = dateutil.parser.parse(publish_date)
                publish_date = dt.strftime('%d/%m/%Y')
            except Exception, e:
                publish_date = ""

        row = [pkg.title.encode('utf-8')]
        row.append(pkg.notes.encode('utf-8') or "")
        row.append(grp)
        row.append(publish_date)
        row.append(pkg.extras.get('release-notes', '').encode('utf-8'))

        writer.writerow(row)



def enqueue_document(user, filename, publisher):
    """
    Uses the provided data to send a job to the priority celery queue so that
    the spreadsheet is processed. We should create a job_started message header_row
    to ensure that the user sees immediately that something is happening.
    """
    from pylons import config
    from ckan import model
    from ckan.model.types import make_uuid
    from ckan.lib.celery_app import celery

    site_user = get_action('get_site_user')(
        {'model': model, 'ignore_auth': True, 'defer_commit': True}, {})

    task_id = make_uuid()

    # Create the task for the queue
    context = json.dumps({
        'username': user.name,
        'site_url': config.get('ckan.site_url_internally') or config.get('ckan.site_url'),
        'apikey': user.apikey,
        'site_user_apikey': site_user['apikey']
    })
    data = json.dumps({
        'file': filename,
        'publisher': publisher.name,
        'publisher_id': publisher.id,
        'jobid': task_id
    })
    celery.send_task("inventory.process", args=[context, data], task_id=task_id, queue='priority')

    # Create a task status.... and update it so that the user knows it has been started.
    inventory_task_status = {
        'entity_id': task_id,
        'entity_type': u'inventory',
        'task_type': u'inventory',
        'key': u'celery_task_id',
        'value': task_id,
        'error': u'',
        'state': 'Started',
        'last_updated': datetime.datetime.now().isoformat()
    }
    inventory_task_context = {
        'model': model,
        'user': user.name,
        'ignore_auth': True
    }
    res = get_action('task_status_update')(inventory_task_context, inventory_task_status)
    return res['id'], inventory_task_status['last_updated']


def render_inventory_header(writer):
    # Add
    #   - Reason for non-release
    writer.writerow(["Department", "Dataset title", "Description of dataset",
                     "Number of resources", "Unpublished", "Status"])

def render_inventory_row(writer, datasets, group):
    """
    Writes out the provided inventory items to the provided writer in
    the correct format.
    """
    def encode(s):
        return s.encode('utf-8')

    for dataset in datasets:
        row = []
        row.append(encode(group.title))          # Group shortname
        row.append(encode(dataset.title))        # Dataset name
        row.append(encode(dataset.notes or "No description").strip())    # Dataset description
        row.append(str(len(dataset.resources)))  # Number of resources
        row.append(encode(unicode(dataset.extras.get('unpublished',False))))
        row.append(encode(dataset.state))        # Status
        writer.writerow(row)


class UploadFileHelper(object):
    """
    A contextmanager for handling file uploads by writing it to disk and
    then returning the relevant file as a fileobj
    """
    def __init__(self, filename, file):
        self.input_file = file
        self.file_path = os.path.join('/tmp', filename)

    def __enter__(self):
        self.output_file = open(self.file_path, 'wb')
        self.input_file.seek(0)

        while True:
            data = self.input_file.read(-1)
            if not data:
                break
            self.output_file.write(data)
            self.output_file.flush()
        self.output_file.close()

        return open(self.file_path, "rb")

    def __exit__(self, type, value, traceback):
        try:
            os.unlink(self.file_path)
        except:
            pass

        return not (type and value)

