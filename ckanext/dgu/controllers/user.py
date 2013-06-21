import ckan.plugins.toolkit as t
import ckan.lib.helpers as h
from ckan.lib.base import BaseController, abort
from ckan.controllers.user import UserController as CoreUserController
c = t.c

class UserController(CoreUserController):
    def me(self, locale=None):
        if not c.user:
            h.redirect_to(locale=locale, controller='user', action='login', id=None)
        user_ref = c.userobj.get_reference_preferred_for_uri()
        # redirect to the user-read instead of user-dashboard
        h.redirect_to(locale=locale, controller='user', action='read', id=user_ref)
