import factory

from ckan import model
import ckanext.dgu.model.schema_codelist as schema_model


class SchemaObj(factory.Factory):
    '''A factory class for creating a schema. Returns an object as that is most to hand.'''

    FACTORY_FOR = schema_model.Schema

    # These are the default params that will be used to create new users.
    url = 'http://schema'
    title = 'Test schema'

    # I'm not sure how to support factory_boy's .build() feature in CKAN,
    # so I've disabled it here.
    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    # To make factory_boy work with CKAN we override _create() and make it call
    # a CKAN action function.
    # We might also be able to do this by using factory_boy's direct SQLAlchemy
    # support: http://factoryboy.readthedocs.org/en/latest/orms.html#sqlalchemy
    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."
        # no action, so just do it manually
        schema = schema_model.Schema(**kwargs)
        model.Session.add(schema)
        model.repo.commit_and_remove()
        return schema