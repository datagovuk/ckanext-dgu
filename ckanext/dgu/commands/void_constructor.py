import os
import sys
import datetime
import logging
from ckan.lib.cli import CkanCommand

log = logging.getLogger('ckanext')

class VoidConstructor(CkanCommand):
    """
    Build VoID files for various endpoints in the system

    Provides VoID data at the /.well-known/void endpoint where it will
    make the data much more discoverable for linked-data systems.

    We need to decide *exactly* what subset of DCAT we wish to provide
    within the RDF but for now, title, description and tags might be a
    reasonable starting point.
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0


    def __init__(self, name):
        super(VoidConstructor, self).__init__(name)
        self.parser.add_option("-o",
                  metavar="FILE", dest="output_file",
                  help="Specifies the output file")

    def command(self):
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        self._build_dataset_root()


    def _build_dataset_root(self):
        """ Build the VoID file at /dataset/.void """
        import ckan.model as model

        if self.options.output_file:
            self.f = open(self.options.output_file, 'w')
        else:
            self.f = sys.stdout
        self._write_header()

        log.info("Retrieving publisher list")
        publishers = model.Session.query(model.Group).filter(model.Group.state=='active')
        log.info("Retrieved %d publishers" % publishers.count())

        for publisher in publishers:
            self._build_publisher_entry(publisher)

        log.info("Retrieving dataset list")
        datasets = model.Session.query(model.Package).filter(model.Package.state=='active')
        log.info("Retrieved %d datasets" % datasets.count())

        for dataset in datasets:
            self._build_dataset_entry(dataset)

    def _write_header(self):
        self.f.write("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n")
        self.f.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        self.f.write("@prefix foaf: <http://xmlns.com/foaf/0.1/> .\n")
        self.f.write("@prefix dcterms: <http://purl.org/dc/terms/> .\n")
        self.f.write("@prefix void: <http://rdfs.org/ns/void#> .\n")
        self.f.write("@prefix dbpedia: <http://dbpedia.org/resource/> .\n")
        self.f.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
        self.f.write("\n")


    def _build_dataset_entry(self, dataset):
        # TODO: Work out why qualified won't work in url_for
        from pylons import config
        from ckan.lib.helpers import url_for

        pub = dataset.get_organization()
        url = config.get('ckan.site_url', '') + url_for(controller='package', action='read', id=dataset.id,
            format='rdf')

        self.f.write(":%s a void:Dataset;\n" % dataset.name)
        self.f.write('    dcterms:title "%s"\n' % dataset.title.encode('utf-8'))
        self.f.write("    dcterms:source <%s>\n" % url)
        self.f.write("    dcterms:publisher :%s\n" % pub.name)
        self.f.write("\n")

    publishers_written = {}

    def _build_publisher_entry(self, publisher):
        """ Writes a publisher entry if we haven't see it before """
        self.f.write(":%s a foaf:Organization\n" % publisher.name)
        self.f.write('    rdfs:label "%s";\n' % publisher.title)
        self.f.write("\n")
            #foaf:homepage <http://www.fu-berlin.de/>;


