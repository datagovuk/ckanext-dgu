import ckan.new_tests.helpers as helpers
from ckan import model
from ckanext.dgu.model import commitment
from ckanext.archiver import model as archiver


class DguFunctionalTestBase(helpers.FunctionalTestBase):
    def setup(self):
        # inherited setup does reset_db()
        super(DguFunctionalTestBase, self).setup()

        # init DGU-specific models
        commitment.init_tables(model.meta.engine)
        archiver.init_tables(model.meta.engine)
