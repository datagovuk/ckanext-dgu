import copy

from ckan import model
from common import ScriptError, remove_readonly_fields

log = __import__("logging").getLogger(__name__)

class PackageMatcher(object):
    def match_ref(self, pkg_name):
        '''Override this and return True or False depending on whether
        the supplied package matches or not. If the matcher requires
        more package information, then return None and the match method
        is run.'''
        pass

    def match(self, pkg):
        '''Override this and return True or False depending on whether
        the supplied package matches or not.'''
        assert NotImplementedError

class BasicPackageMatcher(PackageMatcher):
    def __init__(self, match_field, match_field_value):
        '''Package matching criteria: match_field==match_field_value'''
        self.match_field = match_field
        self.match_field_value = match_field_value
        
    def match(self, pkg):
        value = pkg.get(self.match_field) or \
                pkg['extras'].get(self.match_field)
        if value == self.match_field_value:
            return True
        else:
            return False

class AnyPackageMatcher(PackageMatcher):
    def match(self, pkg):
        return True

class ListedPackageMatcher(PackageMatcher):
    '''Package matcher based on a supplied list of package names.'''
    def __init__(self, pkg_name_list):
        assert iter(pkg_name_list)
        assert not isinstance(pkg_name_list, basestring)
        self.pkg_name_list = set(pkg_name_list)
        
    def match_name(self, pkg_name):
        return pkg_name in self.pkg_name_list

    def match(self, pkg):
        return pkg['name'] in self.pkg_name_list

class PackageChanger(object):
    def change(self, pkg):
        '''Override this to return a changed package dictionary.
        @param pkg: package dictionary
        '''
        assert NotImplementedError

    def resolve_field_value(self, input_field_value, pkg):
        '''Resolves the specified field_value to one
        specific to this package.
        Examples:
          "pollution" -> "pollution"
          "%(name)s" -> "uk-pollution-2008"
        '''
        return input_field_value % pkg

    def flatten_pkg(self, pkg_dict):
        flat_pkg = copy.deepcopy(pkg_dict)
        for name, value in pkg_dict.items()[:]:
            if isinstance(value, (list, tuple)):
                if value and isinstance(value[0], dict) and name == 'resources':
                    for i, res in enumerate(value):
                        prefix = 'resource-%i' % i
                        flat_pkg[prefix + '-url'] = res['url']
                        flat_pkg[prefix + '-format'] = res['format']
                        flat_pkg[prefix + '-description'] = res['description']
                else:
                    flat_pkg[name] = ' '.join(value)
            elif isinstance(value, dict):
                for name_, value_ in value.items():
                    flat_pkg[name_] = value_
            else:
                flat_pkg[name] = value
        return flat_pkg
        

class BasicPackageChanger(PackageChanger):
    def __init__(self, change_field, change_field_value):
        '''Changes: pkg.change_field = change_field_value'''
        self.change_field = change_field
        self.change_field_value = change_field_value
        
    def change(self, pkg):
        flat_pkg = self.flatten_pkg(pkg)
        if pkg.has_key(self.change_field):
            pkg_field_root = pkg
        else:
            pkg_field_root = pkg['extras']
        value = self.resolve_field_value(self.change_field_value, flat_pkg)

        log.info('%s.%s  Value %r -> %r' % \
                 (pkg['name'], self.change_field,
                  flat_pkg.get(self.change_field),
                  value))

        pkg_field_root[self.change_field] = value
        return pkg

class CreateResource(PackageChanger):
    def __init__(self, **resource_values):
        '''Adds new resource with the given values.
        @param resources_values: resource dictionary. e.g.:
                {'url'=xyz, 'description'=xyz}
        '''
        for key in resource_values.keys():
            assert key in model.PackageResource.get_columns()
        self.resource_values = resource_values
        
    def change(self, pkg):
        flat_pkg = self.flatten_pkg(pkg)
        resource = {}
        for key, value in self.resource_values.items():
            resource[key] = self.resolve_field_value(value, flat_pkg)
        resource_index = len(pkg['resources'])
        
        log.info('%s.resources[%i] -> %r' % \
                 (pkg['name'], resource_index, resource))

        pkg['resources'].append(resource)
        return pkg

class NoopPackageChanger(PackageChanger):
    def change(self, pkg):
        log.info('%s  No change' % \
                 (pkg['name']))
        return pkg

class ChangeInstruction(object):
    def __init__(self, matchers=None, changers=None):
        '''Finds packages matching criteria and changes them as specified.
        Matchers are derived from PackageMatcher and any of the matchers
        can match to apply all the changes, which derive from PackageChanger.
        '''
        if isinstance(matchers, PackageMatcher):
            self.matchers = [matchers]
        elif isinstance(matchers, list) or matchers == None:
            self.matchers = matchers
        if isinstance(changers, PackageChanger):
            self.changers = [changers]
        elif isinstance(changers, list) or changers == None:
            self.changers = changers


class MassChanger(object):
    def __init__(self, ckanclient, instructions, dry_run=False, force=False):
        '''
        Changes package properties en masse
        @param ckanclient: instance of ckanclient to make the changes
        @param instructions: (ordered) list of ChangeInstruction objects
        @param dry_run: show matching and potential changes, but do not
                        write the changes back to the server.
        @param force: prevents aborting when there is an error with one package
        '''
        self.ckanclient = ckanclient
        version = self.ckanclient.api_version_get()
        assert int(version) >= 2, 'API Version is %s. Script requires at least Version 2.' % version
        self.instructions = instructions
        self.dry_run = dry_run
        self.force = force
        self._pkg_cache = {}

    def run(self):
        pkg_refs = self.ckanclient.package_register_get()
        for pkg_ref in pkg_refs:
            try:
                pkg = self._get_pkg(pkg_ref)
                instruction = self._match_instructions(pkg_ref)
                if instruction:
                    self._change_package(self._get_pkg(pkg_ref), instruction)
            except ScriptError, e:
                err = 'Problem with package %s: %r' % (pkg_ref, e.args)
                log.error(err)
                if not self.force:
                    log.error('Aborting (avoid this with --force)')
                    raise ScriptError(err)

    def _get_pkg(self, pkg_ref):
        if not self._pkg_cache.has_key(pkg_ref):
            pkg = self.ckanclient.package_entity_get(pkg_ref)
            if self.ckanclient.last_status != 200:
                raise ScriptError('Could not get package ID %s: %r' % \
                      (pkg_ref, self.ckanclient.last_status))
            remove_readonly_fields(pkg)
            self._pkg_cache[pkg_ref] = pkg
        return self._pkg_cache[pkg_ref]
                           
    def _match_instructions(self, pkg_ref):
        for instruction in self.instructions:
            for matcher in instruction.matchers:
                assert isinstance(matcher, PackageMatcher), matcher
                name_match = None
#                name_match = matcher.match_name(pkg_ref)
                if name_match == None:
                    pkg = self._get_pkg(pkg_ref)
                    if matcher.match(pkg):
                        return instruction

    def _change_package(self, pkg, instruction):
        pkg_before = copy.deepcopy(pkg)
        for changer in instruction.changers:
            pkg = changer.change(pkg)

        if pkg == pkg_before:
            log.info('...not changed')
            return
        
        if not self.dry_run:
            self.ckanclient.package_entity_put(pkg)
            if self.ckanclient.last_status == 200:
                log.info('...saved %s:' % pkg['name'])
                log.debug('Package saved: %r' % self.ckanclient.last_message)
            else:
                raise ScriptError('Post package %s error: %s' % (pkg['name'], self.ckanclient.last_message))


class MassChangerNamedPackages(MassChanger):
    def run(self):
        for pkg_ref in self.pkg_name_list:
            try:
                instruction = self._match_instructions(pkg_ref)
                if instruction:
                    self._change_package(self._get_pkg(pkg_ref), instruction)
            except ScriptError, e:
                err = 'Problem with package %s: %r' % (pkg_ref, e.args)
                log.error(err)
                if not self.force:
                    log.error('Aborting (avoid this with --force)')
                    raise ScriptError(err)
