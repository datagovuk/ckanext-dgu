import os
import datetime
import ckan.lib.munge as munge
from ckanext.dgu.plugins_toolkit import (c, NotAuthorized,
    ValidationError, get_action, check_access)
from ckan.lib.search import SearchIndexError

def render_inventory_template(writer):
    # Renders a template for completion by the department admin
    writer.writerow(["Dataset title",
                     "Description of dataset",
                     "Update frequency",
                     "Recommendation"])


def validate_incoming_inventory_header(header_row):
    """
    Simple validation of the header row to make sure we have the 4 headers we
    expect in the right place.
    """
    if len(header_row) < 4:
        return False, "There are not enough columns in the spreadsheet."

    if header_row[0].value.strip() != 'Title' or \
            header_row[1].value.strip() != 'Description' or \
            header_row[2].value.strip() != 'Owner':
        return False, "Header row titles have been changed"


    return True, ""

def process_incoming_inventory_row(row_number, row, default_group_name):
    """
    Reads the provided row and updates the information found in the
    database where appropriate.

    The text of any exception raised will be shown to the user and the
    processing aborted.
    """
    from ckan import model

    title = row[0].value
    description = row[1].value
    publisher_name = row[2].value
    publish_date = row[3].value

    if isinstance(publish_date, datetime.datetime):
        publish_date = publish_date.isoformat()

    group = model.Session.query(model.Group).filter(model.Group.title == publisher_name).first()

    # First validation check, make sure we have enough to either update or create an
    # inventory item
    errors = []
    if not title.strip():
        errors.append("Dataset title")

    if not description.strip():
        errors.append("Description of dataset")

    if not group:
        errors.append("Owner")

    if errors:
        raise Exception("The following fields were missing in row {0}: {1}".format(row_number, ", ".join(errors)))

    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'allow_partial_update': True,
        'extras_as_string': True,
    }


    # Check if we can find the dataset by title (for inventory items)
    # If this happens it's kinda hard to work out which we want.  The group might be different
    # to the one that the user just sent us, it might be that it belongs to someone else.
    editable = []
    existing_pkg = None
    for p in model.Session.query(model.Package).filter(model.Package.title==title).all():
        # We'll do an auth check on all of them to see which we can edit.
        try:
            local_ctx = {'model': model, 'session': model.Session, 'user': c.user, 'for_view': False, 'package': p}
            check_access('package_update', local_ctx)
            if p.extras.get('inventory', False):
                editable.append(p)
        except NotAuthorized, e:
            pass

    # If we can edit only one of them, then we should do that.
    if len(editable) == 1:
        existing_pkg = editable[0]
    elif len(editable) > 1:
        raise Exception("Found {0} existing inventory items with title '{1}' editable by you".format(len(editable), title))
    else:
        existing_pkg = None # Just to be clear...

    if existing_pkg:
        # We have found a single inventory item, accessible to this user, with the same title and
        # we have already completed the auth check.
        model.repo.new_revision()
        existing_pkg.extras['publish-date'] = publish_date
        existing_pkg.notes = description or pkg.notes

        groups = existing_pkg.get_groups()
        if groups and groups[0].title != publisher_name:
            # We need to update the group once we have checked that the current
            # user can add to that group
            # Delete existing membership for package
            mx = model.Session.query(model.Member).filter(model.Member.group_id==groups[0].id).\
                filter(model.Member.table_id==existing_pkg.id).\
                filter(model.Member.table_name=='package').first()
            mx.state = 'deleted'
            model.Session.add(mx)
            m = model.Member(group_id=group.id, table_id=p.id, table_name='package', capacity='public')
            model.Session.add(m)

        model.Session.add(existing_pkg)
        model.Session.commit()

        return (existing_pkg, group, publish_date, "Updated",)

    # Looks like a new inventory item, so we'll create a new one.

    def get_clean_name(s):
        current = s
        counter = 1
        while True:
            current = munge.munge_title_to_name(current)
            if not model.Package.get(current):
                break
            current = "{0}_{1}".format(current,counter)
        return current

    package = {}
    package["title"] = title
    package["name"] = get_clean_name(title)
    package["notes"] = description or " "
    package["access_constraints"] = "Not yet chosen"
    package["api_version"] = "3"
    package['license_id']  = ""
    package['foi-name'] = ""
    package['foi-email'] = ""
    package['foi-web'] = ""
    package['foi-phone'] = ""
    package['contact-email'] = ""
    package['contact-phone'] = ""
    package['contact-name'] = ""
    package['theme-primary'] = ""

    package['groups'] = [{"name": group.name}]

    # Setup inventory specific items
    package['inventory'] = True
    package['publish-date'] = publish_date

    try:
        pkg = get_action("package_create")(context, package)
    except NotAuthorized:
        raise Exception("Not authorised to create this dataset")
    except DataError:
        raise Exception("There was a problem with the integrity of the data")
    except SearchIndexError, e:
        raise Exception("Failed to add the dataset to search index")
    except ValidationError, e:
        raise Exception("There was an error validating the data: %s" % str(e))

    pkg = context['package']

    return (pkg, group, publish_date, "Added",)

def render_inventory_header(writer):
    # Add
    #   - Reason for non-release
    writer.writerow(["Department", "Dataset title", "Description of dataset",
                     "Number of resources", "Inventory item?", "Status"])

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
        row.append(encode(unicode(dataset.extras.get('inventory',False))))
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

