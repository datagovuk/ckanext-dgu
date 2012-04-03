from pylons.i18n import _
from ckan.authz import Authorizer
from ckan.logic import check_access_old
from ckan.logic.auth import get_group_object, get_package_object
from ckan.logic.auth.publisher import _groups_intersect
from ckan.plugins import implements, SingletonPlugin, IAuthFunctions


def dgu_group_update(context, data_dict):
    """
    Group edit permission.  Checks that a valid user is supplied and that the user is 
    a member of the group currently with any capacity.
    """
    model = context['model']
    user = context.get('user','')
    group = get_group_object(context, data_dict)

    if not user:
        return {'success': False, 'msg': _('Only members of this group are authorized to edit this group')} 

    # Sys admins should be allowed to update groups
    if Authorizer().is_sysadmin(unicode(user)):
        return { 'success': True }
            
    # Only allow package update if the user and package groups intersect
    userobj = model.User.get( user )
    if not userobj:
        return { 'success' : False, 'msg': _('Could not find user %s') % str(user) }         

    # Only admins of this group should be able to update this group
    if not _groups_intersect( userobj.get_groups( 'publisher', 'admin' ), [group] ):
        return { 'success': False, 'msg': _('User %s not authorized to edit this group') % str(user) }

    return { 'success': True }
    
    
def dgu_group_create(context, data_dict=None):
    model = context['model']
    user = context['user']
   
    if Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}
    
    return {'success': False, 'msg': _('User %s not authorized to create groups') % str(user)}
    

def dgu_package_update(context, data_dict):
    model = context['model']
    user = context.get('user')
    package = get_package_object(context, data_dict)
    
    if Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}
    
    # Only sysadmins can edit UKLP packages.
    # Note: the harvest user *is* a sysadmin
    if package.extras.get('UKLP', '') == 'True':
        return {'success': False,
                'msg': _('User %s not authorized to edit packages in these groups') % str(user)}

    userobj = model.User.get( user )
    if not userobj or \
       not _groups_intersect( userobj.get_groups('publisher'), package.get_groups('publisher') ):
        return {'success': False, 
                'msg': _('User %s not authorized to edit packages in these groups') % str(user)}

    return {'success': True}

def dgu_dataset_delete(context, data_dict):
    """
    Determines whether a dataset's state can be set to "deleted".

    Currently, only UKLP datasets can be deleted; and only by sysadmin users.
    """
    model = context['model']
    user = context.get('user')
    package = get_package_object(context, data_dict)
    
    if Authorizer().is_sysadmin(unicode(user)) and \
       package.extras.get('UKLP', '') == 'True':
        return {'success': True}
    
    return {'success': False}

def dgu_extra_fields_editable(context, data_dict):
    """
    Determines whether a dataset's extra-fields are editable directly.

    Typically, this is only something we want sysadmins to be able to do.
    """
    user = context.get('user')
    if Authorizer().is_sysadmin(unicode(user)):
        return {'success': True}
    else:
        return {'success': False,
                'msg': _('User %s not authorized to edit a dataset\'s extra fields') % str(user)}
