from common import ScriptError

class ChangeInstruction(object):
    def __init__(self, match_field, match_field_value,
                 change_field, change_field_value):
        '''Finds packages matching a criteria and changes them as specified.
        Package matching criteria: match_field==match_field_value
            note: if match_field=="*" then match all packages not already
                  matched in previous instructions of this mass change.
        Changes: pkg.change_field = change_field_value'''
        self.match_field = match_field
        self.match_field_value = match_field_value
        self.change_field = change_field
        self.change_field_value = change_field_value

class MassChanger(object):
    def __init__(self, ckanclient, instructions, dry_run=False):
        '''
        Changes package properties en masse
        @param ckanclient: instance of ckanclient to make the changes
        @param instructions: (ordered) list of ChangeInstruction objects
        @param dry_run: show matching, but do not make any changes
        '''
        self.ckanclient = ckanclient
        version = self.ckanclient.api_version_get()
        assert int(version) >= 2, 'API Version is %i. Script requires at least Version 2.' % version
        self.instructions = instructions
        self.dry_run = dry_run

    def run(self):
        pkg_ids = self.ckanclient.package_register_get()
        for pkg_id in pkg_ids:
            try:
                pkg = self._get_pkg(pkg_id)
                instruction = self._match_instructions(pkg)
                if instruction:
                    self._change_package(pkg, instruction)
            except ScriptError, e:
                print 'ERROR with package %s: %r' % (pkg_id, e.args)

    def _get_pkg(self, pkg_id):
        pkg = self.ckanclient.package_entity_get(pkg_id)
        # get rid of read-only fields if there
        del pkg['id']
        del pkg['relationships']
        del pkg['ratings_average']
        del pkg['ratings_count']
        del pkg['ckan_url']
        return pkg
                           
    def _match_instructions(self, pkg):
        for instruction in self.instructions:
            if instruction.match_field == '*':
                return instruction
            value = pkg.get(instruction.match_field) or \
                    pkg['extras'].get(instruction.match_field)
            if value == instruction.match_field_value:
                return instruction

    def _change_package(self, pkg, instruction):
        if self.ckanclient.last_status == 200:
            if pkg.has_key(instruction.change_field):
                pkg_field_root = pkg
            else:
                pkg_field_root = pkg['extras']
            
            print '%s.%s  Value %r -> %r' % \
                  (pkg['name'], instruction.change_field,
                   pkg_field_root.get(instruction.change_field),
                   instruction.change_field_value)

            if not self.dry_run:
                pkg_field_root[instruction.change_field] = \
                    instruction.change_field_value
            
                self.ckanclient.package_entity_put(pkg)
                if self.ckanclient.last_status == 200:
                    print 'Done %s' % pkg['name']
                else:
                    raise ScriptError('ERROR %s updating package: %s' % (pkg['name'], self.ckanclient.last_message))
            else:
                raise ScriptError('ERROR %s getting package: %s' % (pkg['name'], self.ckanclient.last_message))
