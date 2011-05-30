# Convert extra key "temporal_coverage_to" to "temporal_coverage-to"
#
# Paste this into a shell
# sudo -u www-data paster --plugin=pylons shell /etc/ckan/dgu/dgu.ini

dry_run = True
from collections import defaultdict
pkg_status = defaultdict(list) # reason: [pkgs]
pkgs = model.Session.query(model.Package)
count = 0
rev = None
def new_rev():
    global rev
    if not rev:
        rev = model.repo.new_revision() 
        rev.author = 'okfn'
        rev.message = 'Correcting temporal coverage'

def commit():
    global rev
    if rev:
        model.commit_and_remove()
        rev = None

for pkg in pkgs:
    count += 1
    if pkg.state != 'active':
        pkg_status['State is %s' % pkg.state].append(pkg.name)
        continue
    pkg_changed = False
    for suffix in ('from', 'to'):
        if pkg.extras.has_key('temporal_coverage_%s' % suffix):
            pkg_changed = True
            new_value = pkg.extras.get('temporal_coverage-%s' % suffix) or \
                        pkg.extras.get('temporal_coverage_%s' % suffix) or ''
            if not dry_run:
                new_rev()
                pkg.extras['temporal_coverage-%s' % suffix] = new_value
                del pkg.extras['temporal_coverage_%s' % suffix]
    if pkg_changed:
        pkg_status['changed'].append(pkg.name)        
    commit()

print 'Working with %i packages' % pkgs.count()
for reason, pkgs in pkg_status.items():
    print '\n  %i: %s : %r' % (len(pkgs), reason, '   '.join(pkgs[:5]))

