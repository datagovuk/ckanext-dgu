import collections
import logging
import datetime
import os
import re
import time
import sys
import resource

import lxml.etree as e

from pylons import config
from ckan.lib.cli import CkanCommand

# No other CKAN imports allowed until _load_config is run,
# or logging is disabled

NSMAP = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dct": "http://purl.org/dc/terms/"
}

class CatalogCommand(CkanCommand):
    """
    The catalog command will generate a DCAT description of the catalog.

    To generate the DCAT description, you should run the following command:

    paster catalog generate <OUTPUT_FILE> -c <PATH_TO_CONFIG>
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 2
    min_args = 2

    def __init__(self, name):
        super(CatalogCommand, self).__init__(name)

    def command(self):
        """
        """
        self._load_config()
        self.log = logging.getLogger(__name__)

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        self.log.info("Database access initialised")

        if len(self.args) != 2:
            self.log.error("You must specify the command and the output file")
            return

        cmd, output = self.args

        if cmd == 'generate':
            self.generate(output)

    def generate(self, output):
        import ckan.model as model
        from ckan.lib.helpers import url_for

        def T(ns, tag):
            # Generate a namespaced tag
            return '{%s}%s' % (NSMAP[ns], tag,)

        def E(ns, tag, text=None):
            # Generate an element with a namespaced tag
            element = e.Element(T(ns, tag), nsmap=NSMAP)
            if text:
                element.text = text
            return element

        def D(package):
            # Build a dataset element from a package
            element = E('dcat', 'dataset')
            ds = E('dcat', 'Dataset')
            ds.attrib[T('rdf', 'about')] = "http://data.gov.uk" + url_for(controller='package',
                action='read', id=package.name, )

            ds.append(E('dct', 'description', e.CDATA(package.notes or u'')))
            ds.append(E('dct', 'identifier', package.name))
            ds.append(E('dct', 'issued', package.metadata_created.isoformat()))
            ds.append(E('dct', 'modified', package.metadata_modified.isoformat()))

            element.append(ds)
            return element

        root = E('rdf','RDF')
        doc = e.ElementTree(root)

        cat = E('dcat', 'Catalog')
        # TODO: Pull this from site-url and root folder.
        cat.attrib[T('rdf', 'about')] = "http://data.gov.uk/data"
        root.append(cat)

        cat.append(E('dct', 'title', 'A DCAT feed of datasets published on data.gov.uk'))
        cat.append(E('dct', 'modified', datetime.datetime.now().isoformat()))
        # TODO: Pull this from site-url and root folder.
        cat.append(E('foaf', 'homepage', 'http://data.gov.uk/data'))

        for dataset in model.Session.query(model.Package)\
                .filter(model.Package.state=='active').yield_per(50):
            self.log.info("%s" % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            cat.append(D(dataset))

        doc.write(output, pretty_print=True, xml_declaration=True, encoding='utf-8')



