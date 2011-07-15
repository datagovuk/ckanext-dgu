import logging

from ckan import model
from ckan.lib.munge import munge_title_to_name
from ckanext.dgu.drupalclient import DrupalClient, DrupalKeyError

log = logging.getLogger(__name__)


def munge_group_name(group_title):
    return munge_title_to_name(group_title)

def group_by_drupal_id(drupal_org_id):
    return model.Session.query(model.Group) \
           .join('_extras', aliased=True) \
           .filter(model.GroupExtra.key=='drupal_id') \
           .filter(model.GroupExtra.value==str(drupal_org_id)) \
           .first()

def start_revision(org_id):
    rev = model.repo.new_revision()
    rev.author = 'okfn_maintenance'
    rev.message = 'Syncing organisation %s.' % org_id    

def end_revision():
    if len(model.Session.dirty) > 1 or model.Session.new:
        # changes have occurred (aside from the revision)
        model.repo.commit_and_remove()
    else:
        # changes have not occurred, so delete revision
        model.Session.rollback()    


def sync(xmlrpc_settings):
    drupal_client = DrupalClient(xmlrpc_settings)

    for org_id in range(10000, 20000):
        sync_organisation(drupal_client, org_id)

def sync_organisation(drupal_client, org_id):
    '''Syncs a drupal organisation to a CKAN group. Will be recursive if
    the parent organisation is not in CKAN yet.
    Revisions and committing are handled by this function.
    '''
    org_id = str(org_id)
    try:
        org_name = drupal_client.get_organisation_name(org_id)
    except DrupalKeyError:
        log.warn('No organisation with id: %s', org_id)
        return

    parent_id = drupal_client.get_department_from_organisation(org_id)
    group = group_by_drupal_id(org_id)
    parent_group = group_by_drupal_id(parent_id)
    if not parent_group and parent_id != org_id:
        # if parent_id == org_id then we have to create the group
        # object, but since the parent_group is the same object,
        # we have to commit it before setting the department_id
        # afterwards.
        sync_organisation(drupal_client, parent_id)
        parent_group = group_by_drupal_id(parent_id)
        assert parent_group
    start_revision(org_id)
    if group:
        group.name = munge_group_name(org_name)
        group.title = org_name
        group.extras['department_id'] = parent_group.id
        group.extras['drupal_id'] = org_id
    else:
        group = model.Group(name=munge_group_name(org_name),
                            title=org_name)
        if parent_group:
            assert parent_id != org_id
            group.extras['department_id'] = parent_group.id
        group.extras['drupal_id'] = org_id
        model.Session.add(group)
    end_revision()
    if not parent_group and parent_id == org_id:
        start_revision(org_id)
        group = group_by_drupal_id(org_id)
        group.extras['department_id'] = group.id
        end_revision()
