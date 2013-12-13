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

class DGUInitDB(CkanCommand):
    """
    Creates, if not present, the database tables specific to DGU
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(DGUInitDB, self).__init__(name)

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
        log.info("Commitment table is setup")

        import ckanext.dgu.model.archive_tasks as a_model
        a_model.init_tables(model.meta.engine)
        log.info("Archive tasks table is setup")

        import ckanext.dgu.model.qa_tasks as q_model
        q_model.init_tables(model.meta.engine)
        log.info("QA tasks table is setup")

        # Migrate archive and QA data only in an empty db
        if model.Session.query(a_model.ArchiveTask).count() == 0:
            log.info("Migrating Archive task data")

            # Do we want to migrate all, or do we want to migrate
            # only the latest information
            for status in  model.Session.query(model.TaskStatus)\
                    .filter(model.TaskStatus.task_type=='archiver')\
                    .filter(model.TaskStatus.key=='status').yield_per(1000):
                c = a_model.ArchiveTask.create(status)
                model.Session.add(c)
            model.Session.commit()

        if model.Session.query(q_model.QATask).count() == 0:
            log.info("Migrating QA task data")
            # Do we want to migrate all, or do we want to migrate
            # only the latest information
            for status in model.Session.query(model.TaskStatus)\
                    .filter(model.TaskStatus.task_type=='qa')\
                    .filter(model.TaskStatus.key=='status').yield_per(1000):
                qt = q_model.QATask.create(status)
                model.Session.add(qt)
            model.Session.commit()
