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

REG = rdflib.Namespace('http://purl.org/linked-data/registry#')
SKOS = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')
OWL = rdflib.Namespace('http://www.w3.org/2002/07/owl#')
LDP = rdflib.Namespace('http://www.w3.org/ns/ldp#')

# DGU_type
DGU_TYPE__CODE_LIST = 'Code list'
DGU_TYPE__ONTOLOGY = 'Ontology'
DGU_TYPE__CONTROLLED_LIST = 'Controlled list'

TTL_PARAM = '?_format=ttl'

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


class LinkedDataRegistryHarvester(object):
    @classmethod
    def harvest_resources(cls, linked_data_registry):
        for res in linked_data_registry.get_harvestable_resources():
            cls.harvest_resource(res, linked_data_registry)

    @classmethod
    def harvest_resource(cls, resource, ldr):
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


#top_uri = 'http://environment.data.gov.uk/registry/def'
top_uri = 'http://codes.wmo.int/'
#top_uri = 'http://codes.wmo.int/49-2'
ldr = LinkedDataRegistry(top_uri)
#res = ldr.get_resource(top_uri)
#sr = [sr for sr in ldr.get_sub_registers(res)][0]
#ldr.get_resource(sr.identifier)
LinkedDataRegistryHarvester.harvest_resources(ldr)
