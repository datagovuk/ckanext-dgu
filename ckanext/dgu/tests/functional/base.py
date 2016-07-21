import ckan.new_tests.helpers as helpers
from ckan import model
from ckanext.dgu.model import commitment
from ckanext.archiver import model as archiver
import ckanext.dgu.model.schema_codelist as schema_model


class DguFunctionalTestBase(helpers.FunctionalTestBase):
    def setup(self):
        # inherited setup does reset_db()
        super(DguFunctionalTestBase, self).setup()

        # init DGU-specific models
        commitment.init_tables(model.meta.engine)
        archiver.init_tables(model.meta.engine)
        schema_model.init_tables(model.meta.engine)
