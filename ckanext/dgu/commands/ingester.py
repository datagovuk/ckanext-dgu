import datetime
import os
import logging
import urlparse
import ckanext.dgu.lib.ingest as ingest

from ckan.lib.cli import CkanCommand


log = logging.getLogger('ckanext')

class Ingester(CkanCommand):
    """
    Reads in reports in spreadsheets and does something with them.

    Commands supported by this paster command are:

        list

            Provides a list of items it knows how to read

        ingest <named-item> <filename>

            Reads in the file from filename and processese it using
            the named-item.  This should be a value returned from a
            call to list


    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n'.join(__doc__.strip().split('\n')[1:])
    max_args = 3
    min_args = 1


    def __init__(self, name):
        super(Ingester, self).__init__(name)

    def command(self):
        self._load_config()

        import ckan.model as model
        from ckan.logic import get_action

        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        def actions_funcs():
            return {'commitments': self.commitments, 'core_datasets': self.core_datasets}

        def write_list(l):
            print "\n".join([ "\t" + x for x in l])

        if len(self.args) == 1 and self.args[0] == 'list':
            write_list(actions_funcs().keys())
        elif len(self.args) == 3 and self.args[0] == 'read':
            if self.args[1] not in actions_funcs():
                log.error("The named-item must be in the list below:")
                write_list(actions_funcs().keys())
                return

            filename = self.args[2]
            if not os.path.exists(filename):
                print "The filename <%s> could not be found" % filename
                return

            actions_funcs()[self.args[1]](filename)

        else:
            print "Unknown command"

    def commitments(self, filename):
        log.info("Ingesting commitments from {0}".format(filename))

        def header_validate(row):
            """ Validate that we have enough columns with the correct titles """
            if len(row) != 7:
                return False, "Not enough columns, expected 7"

            headers = ["Department","Source", "Dataset Name",
                       "Actual commitment text from relevant document",
                       "Further notes", "Committed Date First Published",
                       "Link to DGU record"]
            if sorted(headers) != sorted(row):
                return False, "Was expecting headers to be {0}".format(headers)

            return True, ""

        def row_validate(row):
            """ Validate that we have enough columns and that every column (with
                the exception of 'Further notes' has content """
            if len(row) != 7:
                return False, "Not enough columns, expected 7"

            # A tiny bit of cleanup of the date format
            if isinstance(row[5], datetime.datetime):
                row[5] = row[5].strftime("%d/%m/%Y")
            if isinstance(row[5], float):
                row[5] = str(int(row[5]))

            required = [row[x] for x in xrange(7) if x not in [4]]
            if not all(required):
                return False, "All fields except 'Further notes' are required".format(row)

            return True, ""

        def process_row(row):
            """
            Reads each row and tries to create a new commitment database entry after
            trying to determine if a matching one already exists.
            TODO: Determine what we can use for 'identity'
            """
            org        = row[0]
            source     = row[1]
            name       = row[2]
            text       = row[3]
            notes      = row[4] or ''
            published  = row[5]
            record_url = row[6]



        try:
            ingester = ingest.Ingester(filename)
            ingester.process(process_row, header_validate, row_validate)
        except ingest.IngestException, ie:
            print ie
            log.exception(ie)
            return


    def core_datasets(self, filename):
        log.info("Ingesting core_datasets from {0}".format(filename))

        def header_validate(row):
            """ Validate that we have enough columns with the correct titles """
            if len(row) != 6:
                return False, "Wrong number of columns, expected 6, got {0}".format(len(row))

            return True, ""

        def row_validate(row):
            """ Validate that we have enough columns and that every column (with
                the exception of 'Further notes' has content """
            if len(row) != 6:
                return False, "Wrong number of columns, expected 6"

            # TODO: Re-enable
            #if row[0].strip() == '' or row[2].strip() == '':
            #    return False, "At a minimum group title and dataset url are required"

            return True, ""

        def process_row(row):
            """
            Reads each row and after working out which dataset it is, sets the core-dataset
            extra to be True.
            """
            import ckan.model as model

            # Validation will catch this later, but for now we will just log the problem.
            if row[0].strip() == '' or row[2].strip() == '':
                log.warn(u'Group title and Dataset name are both required - skipping for now')
                return

            group_title = row[0].strip()
            org = model.Session.query(model.Group)\
                .filter(model.Group.title==group_title)\
                .filter(model.Group.state=='active').first()

            dataset_title = row[1].strip()
            dataset_name = self._url_to_dataset_name(row[2].strip())
            pkg = model.Package.get(dataset_name)
            if not pkg:
                # Complain, but carry on.
                raise ingest.IngestException("Failed to find package {0}".format(row[0]), True)

            facet1 = row[4].strip()
            facet2 = row[5].strip()

            if pkg.extras.get('core-dataset', False) == 'true':
                log.info("Skipping {0} as it is already marked as core".format(pkg.name))
                return

            pkg.extras['core-dataset'] = True
            model.Session.add(pkg)
            model.Session.commit()

        try:
            ingester = ingest.Ingester(filename)
            ingester.process(process_row, header_validate, row_validate)
        except ingest.IngestException, ie:
            print ie
            log.exception(ie)
            return


    def _url_to_dataset_name(self, url):
        """ Converts a url to a dataset into the dataset name """
        obj = urlparse.urlparse(url)
        path = obj.path.split('/')
        return path[-1]
