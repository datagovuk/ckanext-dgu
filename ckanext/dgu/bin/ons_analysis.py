from common import ScriptError

from ckanclient import CkanApiError

'''
Looks at ONS packages with trailing underscores and says what department they
are from.
'''

class OnsAnalysis:
    def __init__(self, ckanclient):
        self.ckanclient = ckanclient
        assert self.ckanclient.api_version_get() == '1', self.ckanclient.api_version_get()

    def run(self):
        pkg_names = self.ckanclient.package_register_get()
        pkgs = []
        for pkg_name in pkg_names:
            if pkg_name.endswith('_'):
                pkg = self.ckanclient.package_entity_get(pkg_name)
                if 'ONS' in pkg['extras'].get('import_source', '') and \
                       pkg.get('state', 'active'):
                    dept = pkg['extras'].get('department')
                    try:
                        pkg_associated = self.ckanclient.package_entity_get(pkg_name.rstrip('_'))
                    except CkanApiError:
                        dept_associated = None
                    else:
                        dept_associated = pkg_associated['extras'].get('department')
                    pkgs.append(pkg)
                    print '%r\n-> %r %r' % (pkg_name, dept, dept_associated)
        print '%i packages' % len(pkgs)
        
