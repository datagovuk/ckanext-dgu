import collections
import logging
import datetime
import os
import re
import time
import sys

from pylons import config
from ckan.lib.cli import CkanCommand
# No other CKAN imports allowed until _load_config is run,
# or logging is disabled

class InitDB(CkanCommand):
    """
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(InitDB, self).__init__(name)

    def command(self):
        """
        """
        self._load_config()
        log = logging.getLogger(__name__)

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        #model.repo.new_revision()
        log.info("Database access initialised")

        import ckanext.dgu.model.commitment as c_model
        c_model.init_tables(model.meta.engine)
        log.debug("Commitment table is setup")


class IngestCommitments(CkanCommand):
    """
    Ingests an XLS
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(IngestCommitments, self).__init__(name)

    def command(self):
        """
        """
        self._load_config()
        log = logging.getLogger(__name__)

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

