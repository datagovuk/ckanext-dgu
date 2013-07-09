import logging
from ckan.lib.cli import CkanCommand
import sys
import os
import csv

log = logging.getLogger('ckanext')

class CleanThemes(CkanCommand):
    """
    Export & import dataset Theme assignments as CSV.
    Usage: clean_themes export export_file.csv
       Or: clean_themes import import_file.csv
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 2
    min_args = 2

    headers = [ 
            'name', 
            'primary', 
            'secondary:Health', 
            'secondary:Environment', 
            'secondary:Education', 
            'secondary:Finance', 
            'secondary:Society', 
            'secondary:Defence', 
            'secondary:Transportation', 
            'secondary:Location', 
            'secondary:Spending data', 
            'secondary:Government', 
            'secondary:Spending', 
    ]

    def __init__(self, name):
        super(CleanThemes, self).__init__(name)

    def command(self):
        self._load_config()

        cmd = self.args[0]
        if cmd not in ['export', 'import']:
            log.error("First argument must be 'export' or 'import'. Got: %s" % cmd)
            sys.exit(1)
        filename = self.args[1]

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        if cmd=='export':
            if os.path.exists(filename):
                log.error('refusing to overwrite file: %s' % filename)
                sys.exit(1)
            self.export_csv(model,filename)
        if cmd=='import':
            self.import_csv(model,filename)

    def export_csv(self,model,filename):
        log.info('Exporting to file: %s' % filename)
        with open(filename,'w') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            q = model.Session.query(model.Package)
            count = q.count()
            log.info('Iterating over %d packages...' % count)
            n = 0
            for pkg in q:
                tmp = self._package_to_dict(pkg)
                csv_row = [ tmp.get(x,'') for x in self.headers ]
                writer.writerow(csv_row)
                n += 1
                if (n%100)==0:
                    log.info('[%d/%d] Processing...' % (n,count))
            log.info('Committing file...')

    def import_csv(self,model,filename):
        filename_changelog = 'themes_changelog.csv'
        log.info('Importing file: %s' % filename)
        log.info('Saving changelog to file: %s' % filename_changelog)
        with open(filename_changelog,'w') as file_changelog:
            changelog = csv.writer(file_changelog)
            changelog.writerow(['name','status','detail'])
            log.info('Processing CSV file')
            data = {}
            with open(filename,'r') as f:
                reader = csv.DictReader(f)
                assert set(reader.fieldnames)<=set(self.headers), 'Unexpected incoming CSV headers: %s' % str(list(set(reader.fieldnames)-set(self.headers)))
                for row in reader:
                    data[row['name']] = row
            log.info('CSV datafile contains %d packages.' % len(data))
            q = model.Session.query(model.Package)
            count = q.count()
            log.info('Walking through %d packages in DB...' % count)
            n = 0
            for pkg in q:
                row = data.pop(pkg.name,None)
                if row is None:
                    changelog.writerow([pkg.name,'not_in_csv',''])
                    continue
                # Make changes as appropriate
                tmp = self._package_to_dict(pkg)
                for key in self.headers:
                    before = tmp.get(key,'')
                    after = row.get(key,'')
                    if before!=after:
                        changelog.writerow([row['name'],'change:%s' % key,'"%s"->"%s"'%(before,after)])
                n += 1
                if (n%100)==0:
                    log.info('[%d/%d] Processing...' % (n,count))
            log.info('Committing database...')
            # If data still has entries, these are packages not found in our DB
            for row in data.values():
                changelog.writerow([row.name,'not_in_db',''])

    def _package_to_dict(self,pkg):
        out = {}
        out['name'] = pkg.name
        out['primary'] = pkg.extras.get('theme-primary','')
        secondary = pkg.extras.get('theme-secondary',[])
        if type(secondary) is not list:
            secondary = [secondary]
        for x in secondary:
            out['secondary:'+x] = 'True'
        assert set(out.keys()) <= set(self.headers), 'Unexpected CSV headers generated: %s' % str(list(set(out.keys())-set(self.headers)))
        return out

