from common import ScriptError

log = __import__("logging").getLogger(__name__)

class PackageMatcher(object):
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

class PackageChanger(object):
    def change(self, pkg):
        '''Override this to return a changed package dictionary.
        @param pkg: package dictionary
        '''
        assert NotImplementedError

class BasicPackageChanger(PackageChanger):
    def __init__(self, change_field, change_field_value):
        '''Changes: pkg.change_field = change_field_value'''
        self.change_field = change_field
        self.change_field_value = change_field_value
        
    def change(self, pkg):
        if pkg.has_key(self.change_field):
            pkg_field_root = pkg
        else:
            pkg_field_root = pkg['extras']

        log.info('%s.%s  Value %r -> %r' % \
                 (pkg['name'], self.change_field,
                  pkg_field_root.get(self.change_field),
                  self.change_field_value))

        pkg_field_root[self.change_field] = self.change_field_value
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

    def run(self):
        pkg_ids = self.ckanclient.package_register_get()
        for pkg_id in pkg_ids:
            try:
                pkg = self._get_pkg(pkg_id)
                if self.ckanclient.last_status != 200:
                    raise 'Could not get package ID %s: %r' % \
                          (pkg_id, self.ckanclient.last_status)
                instruction = self._match_instructions(pkg)
                if instruction:
                    self._change_package(pkg, instruction)
            except ScriptError, e:
                err = 'Problem with package %s: %r' % (pkg_id, e.args)
                log.error(err)
                if not self.force:
                    log.error('Aborting (avoid this with --force)')
                    raise ScriptError(err)

    def _get_pkg(self, pkg_id):
        pkg = self.ckanclient.package_entity_get(pkg_id)
        # get rid of read-only fields if they exist
        for read_only_field in ('id', 'relationships', 'ratings_average',
                                'ratings_count', 'ckan_url'):
            if pkg.has_key(read_only_field):
                del pkg[read_only_field]
        return pkg
                           
    def _match_instructions(self, pkg):
        for instruction in self.instructions:
            for matcher in instruction.matchers:
                assert isinstance(matcher, PackageMatcher), matcher
                if matcher.match(pkg):
                    return instruction

    def _change_package(self, pkg, instruction):
        for changer in instruction.changers:
            pkg = changer.change(pkg)
        assert pkg
        
        if not self.dry_run:
            self.ckanclient.package_entity_put(pkg)
            if self.ckanclient.last_status == 200:
                log.info('...saved %s' % pkg['name'])
            else:
                raise ScriptError('Post package %s error: %s' % (pkg['name'], self.ckanclient.last_message))

