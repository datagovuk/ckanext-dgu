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
            if self.ckanclient.last_status != 200:
                raise LoaderError('Search request failed (status %s): %s' % (self.ckanclient.last_status, res))
            if res['count'] > 1:
                raise LoaderError('More than one record matches the unique field: %s=%s' % (self.unique_extra_field, field_value))
            elif res['count'] == 1:
                existing_pkg_name = res['results'][0]
            if existing_pkg_name != pkg_dict['name']:
                # check name is not used by another package
                original_name = pkg_dict['name']
                clashing_pkg = self._get_package(pkg_dict['name'])
                if clashing_pkg and \
                   clashing_pkg['extras'][self.unique_extra_field] == field_value:
                    print 'Warning, search failed to find package %r with ref %r, but luckily the name is what was expected so loader found it anyway.' % (pkg_dict['name'], field_value)
                    existing_pkg_name = clashing_pkg['name']
                else:
                    original_clashing_pkg = clashing_pkg
                    while clashing_pkg:
                        pkg_dict['name'] += '_'
                        clashing_pkg = self.ckanclient.package_entity_get(pkg_dict['name'])
                    if pkg_dict['name'] != original_name:
                        clashing_unique_value = original_clashing_pkg['extras'][self.unique_extra_field]
                        print 'Warning, name %r already exists for package with ref %r so new package renamed to %r with ref %r.' % (original_name, clashing_unique_value, pkg_dict['name'], field_value)

        else:
            existing_pkg = self._get_package(pkg_dict['name'])
            existing_pkg_name = pkg_dict['name'] if existing_pkg else None

        # load package
        if existing_pkg_name:
            self.ckanclient.package_entity_put(pkg_dict, existing_pkg_name)
        else:
            self.ckanclient.package_register_post(pkg_dict)
        if self.ckanclient.last_status != 200:
            raise LoaderError('Error (%s) loading package over API: %s' % (self.ckanclient.last_status, self.ckanclient.last_message))

    def load_packages(self, pkg_dicts):
        '''Loads multiple packages. Prints results and returns numbers.'''
        assert isinstance(pkg_dicts, (list, tuple))
        num_errors = 0
        num_loaded = 0
        for pkg_dict in pkg_dicts:
            print 'Loading %s' % pkg_dict['name']
            try:
                self.load_package(pkg_dict)
            except LoaderError, e:
                print 'Error loading dict "%s": %s' % (pkg_dict['name'], e)
                num_errors += 1
            else:
                num_loaded += 1
        if num_errors == 0 and num_loaded:
            print 'SUCCESS'
        else:
            print '%i ERRORS' % num_errors
        print '%i package loaded' % num_loaded
        return num_loaded, num_errors

    def _get_package(self, pkg_name):
        pkg = self.ckanclient.package_entity_get(pkg_name)
        if self.ckanclient.last_status == 404:
            pkg = None
        elif self.ckanclient.last_status != 200:
            raise LoaderError('Unexpected status (%s) checking for package under name %r: %r') % (self.ckanclient.last_status, pkg_name, pkg)
        return pkg
        
