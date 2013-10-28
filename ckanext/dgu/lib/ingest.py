"""
Ingester is a helper class for reading tabular format files (xls, csv) and
processing them for some purpose.

One a file path is passed to the constructor (assuming it exists) user supplied
functions will be called to validate the file, and these functions must have a
specific signature.

Validator functions (optionally passed to process) should have a signature that
looks like:

    def validator_func(row)

and return a boolean (success) and a message which describes any failure.

The processing function should have the following signature:

    def processor(row)

and should return nothing. If a failure occurs then the function should raise
a IngestException which accepts a message and whether the process should
attempt to continue of fail immediately.
"""
import logging
import messytables
import os

log = logging.getLogger("ckanext")

class IngestException(Exception):
    """
    This exception is expected to be raised by both the Ingester, and the user
    functions provided to process data.
    """
    def __init__(self, err_message, should_continue=False):
        self.should_continue = should_continue
        super(IngestException,self).__init__(err_message)


class Ingester(object):

    def __init__(self, filename):
        """
        When provided with a filename (to a CSV, XLS, or XLSX) the constructor
        will attempt to load the file and ensure that messytables knows how to
        process it.
        """
        self.tableset = None

        try:
            _, ext = os.path.splitext( filename )
            self.tableset = messytables.any_tableset(open(filename, 'r'),
                extension=ext[1:])
        except Exception, e:
            if str(e) == "Unrecognized MIME type: text/plain":
                # Attempt to force the load as a CSV file to work around messytables
                # not recognising text/plain
                self.tableset = messytables.any_tableset(f, mimetype="text/csv")
            else:
                log.exception(e)
                raise Exception(u"Failed to load the file at {0}".format(filename))

    def process(self, processor, header_validator=None, row_validator=None):
        """
        This method will iterate through the tabular data (in the first table/sheet)
        and after running any validators (on headers, and each row) will attempt to
        use the user-supplied processor to handle each row.
        """
        first = True
        count = 0

        for row in self.tableset.tables[0]:

            raw_row = [x.value for x in row]
            if first:
                # Process the validation of the header row if we have
                # been given a validator
                first = False

                if header_validator:
                    ok,err = header_validator(raw_row)
                    if not ok:
                        raise IngestException(err,False)
            else:
                # If the entire row is empty, then we should probably stop
                # processing and explain why but this will then not handle
                # blank rows in the middle of the table. We will raise an
                # exception in this case so that the processor() can decide
                # how to notify the user.
                if not any(raw_row):
                    raise IngestException("Encountered a blank row in the table")

                # Process the individual rows in the file
                if row_validator:
                    ok,err = row_validator(raw_row)
                    if not ok:
                        raise IngestException(err,False)

                # Pass
                try:
                    processor(raw_row)
                    count = count + 1
                except IngestException, ie:
                    if ie.should_continue:
                        print ie
                        continue
                    raise ie

        log.info("Processed {0} rows".format(count))