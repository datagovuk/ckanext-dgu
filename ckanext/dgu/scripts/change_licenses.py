class ScriptError(Exception):
    pass

class ChangeLicenses(object):
    def __init__(self, ckanclient, license_id):
        '''
        Changes licenses of packages.
        @param ckanclient: instance of ckanclient to make the changes
        @param license_id: id of the license to change packages to
        '''
        self.ckanclient = ckanclient
        version = self.ckanclient.api_version_get()
        assert int(version) >= 2, 'API Version is %i. Script requires at least Version 2.' % version
        self.license_id = license_id

    def change_all_packages(self):
        pkg_ids = self.ckanclient.package_register_get()
        for pkg_id in pkg_ids:
            try:
                self.change_package(pkg_id)
            except ScriptError, e:
                print 'ERROR with package %s: %r' % (pkg_id, e.args)

    def change_package(self, pkg_id):
        pkg = self.ckanclient.package_entity_get(pkg_id)
        if self.ckanclient.last_status == 200:
            pkg['license_id'] = self.license_id
            del pkg['id']
            del pkg['relationships']
            del pkg['ratings_average']
            del pkg['ratings_count']
#            del pkg['groups']
            del pkg['ckan_url']
            self.ckanclient.package_entity_put(pkg)
            if self.ckanclient.last_status == 200:
                print 'Done %s' % pkg['name']
            else:
                raise ScriptError('ERROR %s updating package: %s' % (pkg_id, self.ckanclient.last_message))
        else:
            raise ScriptError('ERROR %s getting package: %s' % (pkg_id, self.ckanclient.last_message))
