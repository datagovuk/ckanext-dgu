import logging
from ckan.lib.cli import CkanCommand
from ckan.lib.dictization.model_dictize import package_dictize
import sys
import os
import unicodecsv

log = logging.getLogger('ckanext')

class RefinePackages(CkanCommand):
    """
    Export package data to Google Refine as a CSV. Import it back after cleaning.
    Usage: refine_packages export export_file.csv
       Or: refine_packages import import_file.csv
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 2
    min_args = 2

    # Fields to write to the CSV.
    # To update: See export_row() and import_row()
    csv_headers = [
            'name',
            'publisher',
            'title',
            'description',
            'tags',
            'theme-primary',
            'theme-secondary::Defence',
            'theme-secondary::Education',
            'theme-secondary::Geography',
            'theme-secondary::Economy',
            'theme-secondary::Government',
            'theme-secondary::Health',
            'theme-secondary::Location',
            'theme-secondary::Society',
            'theme-secondary::Spending',
            'theme-secondary::Crime',
            'theme-secondary::Transport',
            ]

    def __init__(self, name):
        super(RefinePackages, self).__init__(name)

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
            self._export_csv(model,filename)
        if cmd=='import':
            self._import_csv(model,filename)

    def _get_secondary_themes(self,rowdict):
        out = set()
        for key,value in rowdict.items():
            if key.startswith('theme-secondary::') and bool(value):
                theme_name = key.split('::')[1]
                assert type(theme_name) in (unicode,str)
                out.add(theme_name)
        return out

    def _export_csv(self,model,filename):
        """Iterate all packages and dump a very large CSV file of chosen data for Refine to crunch."""
        log.info('Exporting to file: %s' % filename)
        with open(filename,'w') as f:
            writer = unicodecsv.DictWriter(f,self.csv_headers)
            writer.writeheader()
            q = model.Session.query(model.Package).filter_by(state='active')
            count = q.count()
            log.info('Iterating over %d packages...' % count)
            n = 0
            def extract_publisher(pkg):
                publisher = pkg.get_organization()
                if publisher:
                    return publisher.title
                return ''
            for pkg in q:
                row = {
                    'name':pkg.name,
                    'title':pkg.title,
                    'description':pkg.notes,
                    'tags':str(pkg.get_tags()),
                    'publisher': extract_publisher(pkg),
                    'theme-primary': pkg.extras.get('theme-primary'),
                }
                ts = pkg.extras.get('theme-secondary',[])
                if type(ts)!=list:
                    ts = [ts]
                for x in ts:
                    row['theme-secondary::%s'%x] = 'True'
                writer.writerow(row)
                n += 1
                if (n%100)==0:
                    log.info('[%d/%d] Processing...' % (n,count))
            log.info('Committing file...')

    def _import_csv(self,model,filename):
        """Read back a CSV file originally created by _export_csv. I assume you changed it in Refine."""
        filename_changelog = 'refine_changelog.csv'
        log.info('Importing file: %s' % filename)
        log.info('Saving changelog to file: %s' % filename_changelog)
        with open(filename_changelog,'w') as file_changelog:
            changelog = unicodecsv.writer(file_changelog)
            changelog.writerow(['name','status','detail'])
            log.info('Processing CSV file')
            data = {}
            with open(filename,'r') as f:
                reader = unicodecsv.DictReader(f)
                assert set(reader.fieldnames)<=set(self.csv_headers), 'Unexpected incoming CSV headers: %s' % str(list(set(reader.fieldnames)-set(self.csv_headers)))
                for row in reader:
                    data[row['name']] = row
            log.info('CSV datafile contains %d packages.' % len(data))
            q = model.Session.query(model.Package).filter_by(state='active')
            count = q.count()
            log.info('Walking through %d packages in DB...' % count)
            n = 0
            for pkg in q:
                row = data.pop(pkg.name,None)
                if row is None:
                    changelog.writerow([pkg.name,'not_in_csv',''])
                    continue
                # Allowing the CSV to modify other fields? Code goes here...
                before = pkg.extras.get('theme-primary')
                after = row.get('theme-primary')
                if (before or after) and (before!=after):
                    changelog.writerow([row['name'],'change:theme-primary',' %s -> %s '%(str(before),str(after))])
                    if after is None:
                        del pkg.extras['theme-primary']
                    else:
                        pkg.extras['theme-primary'] = after
                    model.Session.add(pkg)
                _before = pkg.extras.get('theme-secondary')
                if type(_before)==list:
                    before = set(_before)
                else:
                    before = set()
                    if _before:
                        before.add(_before)
                after = self._get_secondary_themes(row)
                if (before or after) and (before!=after):
                    changelog.writerow([row['name'],'change:theme-secondary',' %s -> %s '%(sorted(list(before)),sorted(list(after)))])
                    pkg.extras['theme-secondary'] = sorted(list(after))
                    model.Session.add(pkg)
                n += 1
                if (n%100)==0:
                    log.info('[%d/%d] Processing...' % (n,count))
            log.info('Committing database...')
            model.Session.commit()
            # If data still has entries, these are packages not found in our DB
            for row in data.values():
                changelog.writerow([row.get('name'),'not_in_db',''])
