# Run this in a shell

dry_run = True
key_date = datetime(2011, 5, 11)
from collections import defaultdict
from datetime import datetime
pkg_status = defaultdict(list) # reason: [pkgs]
pkgs = model.Session.query(model.Package)
print 'Working with %i packages' % pkgs.count()
count = 0
for pkg in pkgs:
    count += 1
    if pkg.state != 'active':
        pkg_status['State is %s' % pkg.state].append(pkg.name)
        continue
    if pkg.extras.get('external_reference') != 'ONSHUB':
        pkg_status['Not ONS'].append(pkg.name)
        continue
    if pkg.revision.timestamp > key_date:
        pkg_status['After date'].append(pkg.name)
        continue
    pkg_status['Delete'].append(pkg.name)
    if not dry_run:
        rev = model.repo.new_revision() 
        rev.author = 'okfn'
        rev.message = 'Deleting obsolete ONS packages'
        pkg.delete()
        model.repo.commit_and_remove()

for reason, pkgs in pkg_status.items():
    print '\n  %i: %s : %r' % (len(pkgs), reason, '   '.join(pkgs[:5]))

