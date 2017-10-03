# In ckanext-dgu/ckanext/dgu/commands.py

import os
import logging
import json
from ckan.lib.cli import CkanCommand
import ckanext.dgu.model.schema_codelist as schema_model

log = logging.getLogger('ckanext')


class UpdateHarvestedSchema(CkanCommand):
    """
    Finds harvested datasets that have resource whose url points at a schema

    Once it has found those resources, it checks if the dataset has a schema
    set and if not, adds it based on the schemas available in the ckan db.
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        schema_urls = {}
        for schema in model.Session.query(schema_model.Schema).all():
            schema_urls[schema.url] = schema.id

        log.info("Schema loaded, found {}".format(len(schema_urls)))

        count = 0
        q = model.Session.query(model.Resource)\
            .filter(model.Resource.url.in_(schema_urls.keys()))\
            .filter(model.Resource.state == 'active')
        for resource in q.all():
            dataset = resource.related_packages()[0]
            print "Processing {}".format(dataset.name)

            extras = dict([(key, value) for key, value in dataset.extras.items()])
            if not extras.get('schema'):
                dataset.extras['schema'] = json.dumps([schema_urls[resource.url]])
                print dataset.extras['schema']
                dataset.save()
                count +=1

        if count:
            model.Session.commit()
        log.info("Updated %d datasets" % count)
