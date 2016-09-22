import logging

from ckan.lib.cli import CkanCommand
# No other CKAN imports allowed until _load_config is run,
# or logging is disabled

class OrganogramCmd(CkanCommand):
    """
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def __init__(self, name):
        super(OrganogramCmd, self).__init__(name)

    def command(self):
        self._load_config()
        self.log = logging.getLogger(__name__)

        cmd = self.args[0]
        if cmd == 'init':
            self.init()
        else:
            raise NotImplementedError

    def init(self):
        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        self.log.info("Database access initialised")

        import ckanext.dgu.model.organogram as o_model
        o_model.init_tables(model.meta.engine)
        self.log.debug("Organogram tables are setup")
