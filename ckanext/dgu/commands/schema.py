import logging

from ckan.lib.cli import CkanCommand
# No other CKAN imports allowed until _load_config is run,
# or logging is disabled


class Schema(CkanCommand):
    """Schema/code list command

    init - initialize the database tables
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def command(self):
        self._load_config()
        self.log = logging.getLogger(__name__)

        cmd = self.args[0]
        if cmd == 'init':
            self.init()

    def init(self):
        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        self.log.info("Database access initialised")

        import ckanext.dgu.model.schema_codelist as s_model
        s_model.init_tables(model.meta.engine)
        self.log.debug("Schema/codelist tables are setup")
