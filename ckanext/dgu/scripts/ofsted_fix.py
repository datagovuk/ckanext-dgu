from collections import defaultdict

from common import ScriptError, remove_readonly_fields

from ckanclient import CkanApiError

class OfstedFix:
    '''Fixes old ONS imports misattributed to Ofsted DGU#780'''
    def __init__(self, ckanclient, dry_run):
        self.ckanclient = ckanclient
        self.dry_run = dry_run

    def run(self):
        limit = 100
        def search(page=None):
            opts = {
#                'external_reference': 'ONSHUB',
                    'limit': limit}
            if page != None:
                opts['offset'] = page * limit
            return self.ckanclient.package_search(
                'Education',
#                'Source agency: Education',
                opts)
        res = search()
        print 'Found %i packages possibly related.' % res['count']
        pkgs_done = []
        pkgs_rejected = defaultdict(list) # reason: [pkgs]
        for page in range(res['count'] / limit):
            res = search(page)
            pkg_refs = res['results']
            for pkg_ref in pkg_refs:
                pkg = self.ckanclient.package_entity_get(pkg_ref)
                if 'ONS' not in pkg['extras'].get('import_source', ''):
                    pkgs_rejected['Not imported from ONS'].append(pkg)
                    continue
                if pkg.get('state', 'active') != 'active':
                    pkgs_rejected['Package state = %r' % pkg.get('state')].append(pkg)
                    continue
                source_agency = '|'.join([line.replace('Source agency:', '').strip() for line in pkg['notes'].split('\n') if 'Source agency' in line])
                if source_agency != 'Education':
                    pkgs_rejected['Source agency = %r' % source_agency].append(pkg)
                    continue
                if 'Department for Education' in pkg['extras'].get('department', ''):
                    pkgs_rejected['Department = %r' % pkg['extras'].get('department', '')].append(pkg)
                    continue

                pkg_name = pkg['name']
                dept = pkg['extras'].get('department')
                agency = pkg['extras'].get('agency')
                author = pkg['author']
                print '%s :\n %r %r %r' % (pkg_name, dept, agency, author)
                if not self.dry_run:
                    pkg['extras']['department'] = 'Department for Education'
                    pkg['extras']['agency'] = ''
                    pkg['author'] = 'Department for Education'
                    remove_readonly_fields(pkg)
                    self.ckanclient.package_entity_put(pkg)
                    print '...done'
                pkgs_done.append(pkg)
        print 'Processed %i packages' % len(pkgs_done)
        print 'Rejected packages:'
        for reason, pkgs in pkgs_rejected.items():
            print '  %i: %s' % (len(pkgs), reason)
