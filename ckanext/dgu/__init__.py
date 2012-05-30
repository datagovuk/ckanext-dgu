# this is a namespace package
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

__version__ = '0.4'

# == Monkey Patching ==
def dgu_linked_user(user):  # Overwrite h.linked_user
    from ckan import model
    if user in [model.PSEUDO_USER__LOGGED_IN, model.PSEUDO_USER__VISITOR]:
        return user
    if not isinstance(user, model.User):
        user_name = unicode(user)
        user = model.User.get(user_name)
        if not user:
            return '(no id)'
    if user:
        _name = user.id
        _icon = gravatar(None, 20)
        return _icon + link_to(_name,
                       url_for(controller='user', action='read', id=_name))
#Disabled for now as it borks install
#from ckan.lib.base import h
#h.linked_user = dgu_linked_user

