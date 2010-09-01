'''
Takes a package dictionary and loads into CKAN via the API.
Checks to see if it already exists by name and preferably a unique field in
the extras too.
Uses ckanclient.
'''
import re
import copy

import ckanclient

class LoaderError(Exception):
    pass

class LoadSettings(object):
    '''Abstract base class for settings for how the PackageLoader
    finds existing packages and modifies them according to the pkg_dicts
    it is passed in.'''
    pass

class ReplaceByName(LoadSettings):
    '''Loader finds a package based on its name.
    Load replaces the package with the supplied pkg_dict.'''
    pass

class ReplaceByExtraField(LoadSettings):
    '''Loader finds a package based on a unique id in an extra field.
    Loader replaces the package with the supplied pkg_dict.'''
    def __init__(self, package_id_extra_key):
        assert package_id_extra_key
        self.package_id_extra_key = package_id_extra_key

class ResourceSeries(LoadSettings):
    '''Loader finds package based on a specified field and checks to see
    if most fields (listed in field_keys_to_expect_invariant) match the
    pkg_dict. Loader then inserts the resources in the pkg_dict into
    the package and updates any fields that have changed (e.g. last_updated).
    It checks to see if the particular resource is already in the package
    by a custom resource ID which is contained in the description field,
    as a word containing the given prefix.
    '''
    def __init__(self, field_keys_to_find_pkg_by, resource_id_prefix,
                 field_keys_to_expect_invariant=None):
        assert field_keys_to_find_pkg_by and resource_id_prefix
        assert isinstance(field_keys_to_find_pkg_by, (list, tuple))
        self.field_keys_to_find_pkg_by = field_keys_to_find_pkg_by
        self.resource_id_prefix = resource_id_prefix
        self.field_keys_to_expect_invariant = field_keys_to_expect_invariant \
                                              or []

class PackageLoader(object):
    def __init__(self, ckanclient, settings=None):
        '''
        Loader for packages into a CKAN server. Takes package dictionaries
        and loads them using the ckanclient.

        It checks to see if a package of the same name is already on the
        CKAN server and if so, updates it with the new info.

        @param ckanclient - ckanclient object, which contains the
                            connection to CKAN server
        @param settings - specifies how the loader finds existing packages
                          and loads in the pkg_dict data. The default is
                          ReplaceByName().
        '''
        self.settings = settings or ReplaceByName()
        assert isinstance(self.settings, LoadSettings)
        assert type(self.settings) != LoadSettings # i.e. not the abstract obj
        
        # Note: we pass in the ckanclient (rather than deriving from it), so
        # that we can choose to pass a test client instead of a real one.
        self.ckanclient = ckanclient
    
    def load_package(self, pkg_dict):
        # see if the package is already there
        existing_pkg_name = None
        if isinstance(self.settings, ReplaceByExtraField):
            find_pkg_by_keys = [self.settings.package_id_extra_key]
        elif isinstance(self.settings, ResourceSeries):
            find_pkg_by_keys = self.settings.field_keys_to_find_pkg_by
        elif isinstance(self.settings, ReplaceByName):
            find_pkg_by_keys = ['name']
        existing_pkg_name, existing_pkg = \
                           self._find_package_by_fields(find_pkg_by_keys,
                                                        pkg_dict)

        # if creating a new package, check the name is available
        if not existing_pkg_name:
            self._ensure_pkg_name_is_available(pkg_dict)

        # load package
        if existing_pkg_name:
            if isinstance(self.settings, ResourceSeries):
                if not existing_pkg:
                    existing_pkg = self.ckanclient.package_entity_get(existing_pkg_name)
                    pkg_dict = self._merge_resources(existing_pkg, pkg_dict)
            self.ckanclient.package_entity_put(pkg_dict, existing_pkg_name)
        else:
            self.ckanclient.package_register_post(pkg_dict)
        if self.ckanclient.last_status != 200:
            raise LoaderError('Error (%s) loading package over API: %s' % (self.ckanclient.last_status, self.ckanclient.last_message))
        pkg_dict = self.ckanclient.last_message
        return pkg_dict

    def load_packages(self, pkg_dicts):
        '''Loads multiple packages.
        @return results and resulting package names/ids.'''
        assert isinstance(pkg_dicts, (list, tuple))
        num_errors = 0
        num_loaded = 0
        pkg_ids = []
        pkg_names = []
        for pkg_dict in pkg_dicts:
            print 'Loading %s' % pkg_dict['name']
            try:
                pkg_dict = self.load_package(pkg_dict)
            except LoaderError, e:
                print 'Error loading dict "%s": %s' % (pkg_dict['name'], e)
                num_errors += 1
            else:
                pkg_ids.append(pkg_dict['id'])
                pkg_names.append(pkg_dict['name'])
                num_loaded += 1
        return {'pkg_names':pkg_names,
                'pkg_ids':pkg_ids,
                'num_loaded':num_loaded,
                'num_errors':num_errors}

    def add_pkg_to_group(self, pkg_name, group_name):
        return self.add_pkgs_to_group([pkg_name], group_name)

    def add_pkgs_to_group(self, pkg_names, group_name):
        for pkg_name in pkg_names:
            assert not self.ckanclient.is_id(pkg_name), pkg_name
        assert not self.ckanclient.is_id(group_name), group_name
        group_dict = self.ckanclient.group_entity_get(group_name)
        if self.ckanclient.last_status == 404:
            raise LoaderError('Group named %r does not exist' % group_name)
        elif self.ckanclient.last_status != 200:
            raise LoaderError('Unexpected status (%s) checking for group name %r: %r') % (self.ckanclient.last_status, group_name, group_dict)
        group_dict['packages'] = (group_dict['packages'] or []) + pkg_names
        group_dict = self.ckanclient.group_entity_put(group_dict)
        if self.ckanclient.last_status != 200:
            raise LoaderError('Unexpected status (%s) putting group entity: %s' % (self.ckanclient.last_status, group_dict))

    def _get_package(self, pkg_name):
        pkg = self.ckanclient.package_entity_get(pkg_name)
        if self.ckanclient.last_status == 404:
            pkg = None
        elif self.ckanclient.last_status != 200:
            raise LoaderError('Unexpected status (%s) checking for package under name %r: %r') % (self.ckanclient.last_status, pkg_name, pkg)
        return pkg
        
    def _find_package_by_fields(self, field_keys, pkg_dict):
        '''Looks for a package that has matching keys to the pkg supplied.
        Requires a unique match or it raises LoaderError.
        @return (pkg_name, pkg) - pkg_name - the name of the matching
                                  package or None if there is none.
                                  pkg - the matching package dict if it
                                  happens to have been requested,
                                  otherwise None
        '''
        if field_keys == ['name']:
            pkg = self._get_package(pkg_dict['name'])
            pkg_name = pkg_dict['name'] if pkg else None
        else:
            pkg = None
            search_options = {}
            has_a_value = False
            for field_key in field_keys:
                field_value = pkg_dict.get(field_key) or pkg_dict['extras'].get(field_key)
                search_options[field_key] = field_value
                if field_value:
                    has_a_value = True
            if not has_a_value:
                raise LoaderError('Package %r has blank values for identifying fields: %r' % (pkg_dict['name'], field_keys))

            res = self.ckanclient.package_search(q='', search_options=search_options)
            if self.ckanclient.last_status != 200:
                raise LoaderError('Search request failed (status %s): %s' % (self.ckanclient.last_status, res))
            if res['count'] > 1:
                raise LoaderError('More than one record matches the unique field: %s=%s' % (unique_extra_field, field_value))
            elif res['count'] == 1:
                pkg_name = res['results'][0]
            else:
                pkg_name = None

        if pkg_name != pkg_dict['name']:
            # Just in case search is not indexing well, look for the
            # package under its name as well
            pkg = self._get_package(pkg_dict['name'])
            if pkg:
                matches = True
                for key, value in search_options.items():
                    if hasattr(pkg, key):
                        if getattr(pkg, key) != value:
                            matches = False
                            break
                    else:
                        if pkg['extras'].get(key) != value:
                            matches = False
                            break
                if matches:
                    print 'Warning, search failed to find package %r with ref %r, but luckily the name is what was expected so loader found it anyway.' % (pkg_dict['name'], field_value)
                    pkg_name = pkg['name']
        return pkg_name, pkg 

    def _ensure_pkg_name_is_available(self, pkg_dict):
        '''Checks the CKAN db to see if the name for this package has been
        already taken, and if so, changes the pkg_dict to have another
        name that is free.
        @return nothing - changes the name in the pkg_dict itself
        '''
        preferred_name = pkg_dict['name']
        clashing_pkg = self._get_package(pkg_dict['name'])

        original_clashing_pkg = clashing_pkg
        while clashing_pkg:
            pkg_dict['name'] += '_'
            clashing_pkg = self.ckanclient.package_entity_get(pkg_dict['name'])

        if pkg_dict['name'] != preferred_name:
            print 'Warning, name %r already exists so new package renamed to %r.' % (preferred_name, pkg_dict['name'])

    def _get_resource_id(self, res):
        words = re.split('\s', res['description'])
        for word in words:
            if word.startswith(self.settings.resource_id_prefix):
                return word[len(self.settings.resource_id_prefix):]

    def _merge_resources(self, existing_pkg, pkg):
        '''Takes an existing_pkg and merges in resources from the pkg.
        '''
        # check invariant fields aren't different
        warnings = []
        for key in self.settings.field_keys_to_expect_invariant:
            if key in existing_pkg or key in pkg:
                if existing_pkg.get(key) != pkg.get(key):
                    warnings.append('%s: %r -> %r' % (key, existing_pkg.get(key), pkg.get(key)))
            else:
                if existing_pkg['extras'].get(key) != pkg['extras'].get(key):
                    warnings.append('%s: %r -> %r' % (key, existing_pkg['extras'].get(key), pkg['extras'].get(key)))
                
        if warnings:
            print 'Warning: uploading package \'%s\' and surprised to see changes in these values:\n%s' % (existing_pkg['name'], '; '.join(warnings))

        # copy over all fields but use the existing resources
        merged_dict = copy.deepcopy(pkg)
        merged_dict['resources'] = copy.deepcopy(existing_pkg['resources'])

        # merge resources
        for pkg_res in pkg['resources']:
            # look for resource ID already being there
            pkg_res_id = self._get_resource_id(pkg_res)
            for i, existing_res in enumerate(merged_dict['resources']):
                res_id = self._get_resource_id(existing_res)
                if res_id == pkg_res_id:
                    # edit existing resource
                    merged_dict['resources'][i] = pkg_res
                    break
            else:
                # insert new res
                merged_dict['resources'].append(pkg_res)

        return merged_dict
                
