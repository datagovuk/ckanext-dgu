'''
Takes a package dictionary and loads into CKAN via the API.
Checks to see if it already exists by name and preferably a unique field in
the extras too.
Uses ckanclient.
'''

import ckanclient

class LoaderError(Exception):
    pass

class PackageLoader(object):
    def __init__(self, ckanclient, unique_extra_field=None):
        # Passing in the ckanclient (rather than deriving from it, so
        # that we can choose to pass it a test client.
        self.ckanclient = ckanclient
        self.unique_extra_field = unique_extra_field
    
    def load_package(self, pkg_dict):
        # see if the package is already there
        existing_pkg_name = None
        if self.unique_extra_field:
            field_value = pkg_dict['extras'][self.unique_extra_field]
            search_options = {self.unique_extra_field:field_value}
            res = self.ckanclient.package_search(q='', search_options=search_options)
            if res['count'] > 1:
                raise LoaderError('More than one record matches the unique field: %s=%s' % (self.unique_extra_field, field_value))
            elif res['count'] == 1:
                existing_pkg_name = res['results'][0]
        else:
            existing_pkg_name = pkg_dict['name'] if \
                     self.ckanclient.package_entity_get(pkg_dict['name']) else None

        # load package
        if existing_pkg_name:
            self.ckanclient.package_entity_put(pkg_dict, existing_pkg_name)
        else:
            self.ckanclient.package_register_post(pkg_dict)
        if self.ckanclient.last_status != 200:
            raise LoaderError('Error (%s) loading package over API: %s' % (self.ckanclient.last_status, self.ckanclient.last_message))
