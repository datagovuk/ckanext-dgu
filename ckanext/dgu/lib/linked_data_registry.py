'''
Library for accessing a Linked Data Registry (written by Epimorphics) and
converting the datasets/codelists into CKAN dataset dicts etc

Linked Data Registries are currently at the 'proof of concept' stage. Current servers include:
* http://environment.data.gov.uk/registry/
* http://codes.wmo.int/

Registries contain entites which are ignored:
* system content
* registers that are just containers for other registers
'''

import rdflib
from rdflib.namespace import RDF, RDFS
import uuid
import logging

from ckan.common import OrderedDict
from ckanext.harvest.harvesters.base import HarvesterBase
import ckan.plugins as p

from ckanext.dgu.lib.formats import Formats

REG = rdflib.Namespace('http://purl.org/linked-data/registry#')
SKOS = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')
OWL = rdflib.Namespace('http://www.w3.org/2002/07/owl#')
LDP = rdflib.Namespace('http://www.w3.org/ns/ldp#')
DCT = rdflib.Namespace('http://purl.org/dc/terms/')

# DGU_type
DGU_TYPE__CODE_LIST = 'Code list'
DGU_TYPE__ONTOLOGY = 'Ontology'
DGU_TYPE__CONTROLLED_LIST = 'Controlled list'

TTL_PARAM = '?_format=ttl'
METADATA_PARAM = '&_view=with_metadata'

def printable_uri(uri):
    for namespace, abbrev in ((REG, 'reg'), (SKOS, 'skos'),
                              (OWL, 'owl'), (LDP, 'ldp')):
        uri = uri.replace(str(namespace), abbrev + ':')
    return uri

class LinkedDataRegistry(object):
    def __init__(self, top_level_uri):
        self.graphs = {}  # URI: rdflib.Graph()
        self.top_level_uri = top_level_uri
        self.get_resource(top_level_uri)

    #def _graph_has_resource(self, uri):
    #    return bool([1 for t in self.graph.resource(uri).predicates()])

    def get_resource(self, uri):
        '''Returns the full details of the URI by resolving it directly.'''
        if str(uri) not in self.graphs:
            # need to download it
            url = uri + TTL_PARAM
            self.graphs[str(uri)] = rdflib.Graph()
            self.graphs[str(uri)].parse(url)
        res = self.graphs[str(uri)].resource(uri)
        return res

    def has_sub_registers(self, register):
        for subreg in register[REG.subregister]:
            return True
        return False

    def get_sub_registers(self, register):
        for subreg in register[REG.subregister]:
            yield subreg.identifier

    def has_member_items(self, register):
        # If a register has member items, it returns one
        member_generator = self.get_member_items(register)
        if member_generator:
            try:
                return member_generator.next()
            except StopIteration:
                return False
        return False

    def get_member_items(self, register):
        graph = self.graphs[str(register.identifier)]
        for subj_uri in set(graph.subjects()):
            if type(subj_uri) == rdflib.term.BNode:
                # not sure where the blank nodes are from
                continue
            if subj_uri == register.identifier:
                # ignore triples about itself - we just want its children
                continue
            subj = graph.resource(subj_uri)
            types = [t.identifier for t in subj[RDF.type]]
            if REG.Register in types:
                # ignore sub-registers
                continue
            yield subj  # NB it's only the triples given when resolving its parent

    def should_harvest_register(self, register):
        # Harvest if it contains a member item (not expecting sub-registers)
        # i.e. Don't harvest if it has sub-registers or no member itms
        has_no_sub_reg = not self.has_sub_registers(register)
        a_member = self.has_member_items(register)
        if has_no_sub_reg and not a_member:
            print '!!!        No sub registers but no members'
            return False
        if not has_no_sub_reg and a_member:
            print '!!!        Sub registers and member: ', a_member[RDFS.label].next()
            return True
        if has_no_sub_reg and a_member:
            # Normal
            #print '           Member and no sub registers: ', a_member[RDFS.label].next()
            return True
        return False

    def get_harvestable_resources(self):
        return self._get_harvestable_resources(self.top_level_uri, 0)

    def _get_harvestable_resources(self, uri, recurses):
        print '%s %s' % (' ' * recurses, str(uri))
        res = self.get_resource(uri)
        if self.should_harvest_register(res):
            yield res
        else:
            for subres_uri in self.get_sub_registers(res):
                if '/system/' in subres_uri:
                    print 'Skipping system register: ', subres_uri
                    continue
                for res in self._get_harvestable_resources(subres_uri, recurses + 1):
                    yield res


class LinkedDataRegistryHarvester(HarvesterBase, p.SingletonPlugin):
    @classmethod
    def harvest_resources(cls, linked_data_registry):
        for res in linked_data_registry.get_harvestable_resources():
            pkg_dict, action = cls.get_pkg_dict(res, linked_data_registry)
            cls.create_or_update(pkg_dict, action)

    @classmethod
    def print_resource(cls, resource, ldr):
        print '           Harvest this!'
        types = sorted([printable_uri(t.identifier) for t in resource[RDF.type]])
        dgu_type = cls.get_dgu_type(resource)
        print '           DGU Type: %s (based on: %s)' % (dgu_type, ', '.join(types))
        print '           Label: %s' % resource[RDFS.label].next()
        print '           Members:'
        count = 0
        for member in ldr.get_member_items(resource):
            types = [t.identifier.split('#')[-1].split('/')[-1] for t in member[RDF.type]]
            print '             %s [%s]' % (member[RDFS.label].next(), '/'.join(types))
            count += 1
            if count == 3:
                print '             ...'
                break

    @classmethod
    def get_pkg_dict(cls, resource, ldr):
        from ckan import model

        pkg_dict = OrderedDict()
        extras = OrderedDict()
        uri = str(resource.identifier)
        pkg_dict['title'] = unicode(resource[RDFS.label].next())
        extras['registry_uri'] = uri

        # Create or update?
        pkg = model.Session.query(model.Package) \
                .filter_by(state='active') \
                .join(model.PackageExtra) \
                .filter_by(state='active') \
                .filter_by(key='registry_uri') \
                .filter_by(value=uri).first()
        if pkg:
            pkg_dict['id'] = pkg.id
            pkg_dict['name'] = pkg.name
            action = 'update'
        else:
            pkg_dict['id'] = unicode(uuid.uuid4())
            pkg_dict['name'] = cls._gen_new_name(pkg_dict['title'])
            action = 'new'

        dgu_type = cls.get_dgu_type(resource)
        extras['data_standard_type'] = dgu_type

        resources = []
        for format_display, format_extension, format_dgu in (
                ('RDF ttl', 'ttl', 'RDF'),
                ('RDF/XML', 'rdf', 'RDF'),
                ('JSON-LD', 'jsonld', 'JSON')):
            url = uri + '?_format=%s' % format_extension
            assert format_dgu in Formats().by_display_name()
            resources.append({'description': '%s as %s' % (dgu_type, format_display),
                              'url': url,
                              'format': format_dgu,
                              'resource_type': 'file'})
            resources.append({'description': '%s and metadata as %s' % (dgu_type, format_display),
                              'url': url + METADATA_PARAM,
                              'format': format_dgu,
                              'resource_type': 'file'})

        pkg_dict['notes'] = unicode(resource[DCT.description].next())
        licence_url = str(resource[DCT.license].next())
        if 'open-government-licence' in licence_url:
            pkg_dict['licence_id'] = 'uk-ogl'
        else:
            extras['licence_url'] = licence_url
            # not sure how this will display as just as URL
        pkg_dict['owner_org'] = cls.get_publisher(resource).id
        resources.append({'description': 'Web page for this %s on a Linked Data Registry' % dgu_type,
                          'url': uri,
                          'format': 'HTML',
                          'resource_type': 'documentation'})
        metadata = cls.get_resource_metadata(uri)
        status = metadata[REG.status].next()
        extras['status'] = str(status).split('#')[-1]
        extras['harvested_version'] = str(metadata[OWL.versionInfo].next())
        extras['data_standard_type'] = dgu_type
        pkg_dict['type'] = 'data-standard'

        pkg_dict['extras'] = [{'key': k, 'value': v} for k, v in extras.items()]
        pkg_dict['resources'] = resources
        return pkg_dict, action

    @classmethod
    def get_resource_metadata(cls, uri):
        url = uri + TTL_PARAM + METADATA_PARAM
        graph = rdflib.Graph()
        graph.parse(url)
        uri_parts = uri.split('/')
        uri_parts[-1] = '_' + uri_parts[-1]
        metadata_uri = '/'.join(uri_parts)
        return graph.resource(metadata_uri)

    @classmethod
    def get_publisher(cls, resource):
        from ckan import model

        publisher_uri = str(resource[DCT.publisher].next().identifier)
        assert publisher_uri
        publisher_url = publisher_uri + TTL_PARAM
        publisher_graph = rdflib.Graph().parse(publisher_url)
        publisher_resource = publisher_graph.resource(publisher_uri)
        publisher_label = unicode(publisher_resource[RDFS.label].next())
        results = model.Group.search_by_name_or_title(publisher_label, is_org=True).all()
        assert len(results) == 1, '%s %r' % (publisher_label, results)
        return results[0]

    @classmethod
    def get_dgu_type(cls, resource):
        rdf_types = set(t.identifier for t in resource[RDF.type])
        # get rid of RDF types not related to the DGU type
        rdf_types -= set((REG.Register, LDP.Container))
        if len(rdf_types) > 1:
            print '!!!       More than one DGU type possible!', \
                  ', '.join(printable_uri(t) for t in rdf_types)
        if OWL.Ontology in rdf_types:
            return DGU_TYPE__ONTOLOGY
        elif SKOS.ConceptScheme in rdf_types:
            return DGU_TYPE__CODE_LIST
        elif SKOS.Collection in rdf_types:
            return DGU_TYPE__CODE_LIST
        else:
            return DGU_TYPE__CONTROLLED_LIST

    @classmethod
    def create_or_update(cls, pkg_dict, action):
        from ckan import model
        from ckan.model import Session
        log = __import__('logging').getLogger(__name__)

        #TODO deal with 'HarvestObject.current' etc
        # c.f. https://github.com/okfn/ckanext-geodatagov/blob/master/ckanext/geodatagov/harvesters/arcgis.py#L219
        #if action == 'new':
        #    package_schema = logic.schema.default_create_package_schema()
        #else:
        #    package_schema = logic.schema.default_update_package_schema()
        class MockHarvestObject: pass
        harvest_object = MockHarvestObject()
        harvest_object.guid = pkg_dict['name']

        context = {'model':model, 'session':Session, 'user':'harvest',
                   'api_version': 3, 'extras_as_string': True} #TODO: user

        if action == 'new':
            try:
                package_id = p.toolkit.get_action('package_create')(context, pkg_dict)
                log.info('Created new package %s with guid %s', package_id, harvest_object.guid)
            except p.toolkit.ValidationError, e:
                print '!!! Validation error:', e.error_summary
                #cls._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                return False
        elif action == 'update':
            try:
                package_id = p.toolkit.get_action('package_update')(context, pkg_dict)
                log.info('Updated package %s with guid %s', package_id, harvest_object.guid)
            except p.toolkit.ValidationError,e:
                print '!!! Validation error:', e.error_summary
                #cls._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                return False

        model.Session.commit()
        return True

if __name__ == '__main__':
    import sys
    from ckanext.dgu.bin import common
    args = sys.argv[1:]
    if len(args) != 1:
        print 'Just one argument - the ckan.ini'
        sys.exit(1)
    config_ini = args[0]
    print 'Loading CKAN config...'
    common.load_config(config_ini)
    common.register_translator()
    print 'Done'
    # Setup logging to print debug out for local stuff only
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.WARNING)
    themeLogger = logging.getLogger(__name__)
    themeLogger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    themeLogger.addHandler(handler)
    #logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    top_uri = 'http://environment.data.gov.uk/registry/def'
    #top_uri = 'http://codes.wmo.int/'
    #top_uri = 'http://codes.wmo.int/49-2'
    ldr = LinkedDataRegistry(top_uri)
    #res = ldr.get_resource(top_uri)
    #sr = [sr for sr in ldr.get_sub_registers(res)][0]
    #ldr.get_resource(sr.identifier)
    #LinkedDataRegistryHarvester.harvest_resources(ldr)
    res_uri = 'http://environment.data.gov.uk/registry/def/catchment-planning/RiverBasinDistrict'
    pkg_dict, action = LinkedDataRegistryHarvester.get_pkg_dict(ldr.get_resource(res_uri), ldr)
    LinkedDataRegistryHarvester.create_or_update(pkg_dict, action)

