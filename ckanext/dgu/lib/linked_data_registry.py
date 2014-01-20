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

TTL_PARAM = '?_format=ttl'

class LinkedDataRegistry(object):
    def __init__(self, top_level_uri):
        self.graph = rdflib.Graph()
        self._resources_got = set()
        #self.top = rdflib.Namespace(top_level_url)
        self.top_level_uri = top_level_uri
        self.get_resource(top_level_uri)

    def _graph_has_resource(self, uri):
        return bool([1 for t in self.graph.resource(uri).predicates()])

    def get_resource(self, uri, resolve=True):
        '''Returns the full details of the URI by resolving it directly.'''
        if uri not in self._resources_got and resolve:
            # need to download it
            url = uri + TTL_PARAM
            self.graph.parse(url)
            self._resources_got.add(uri)
            if not self._graph_has_resource(uri):
                raise Exception('Downloaded URI that doesn\'t have any data '
                                'about itself')
        elif not resolve and not self._graph_has_resource(uri):
            raise Exception('No triples held for URI: %s' % uri)
        res = self.graph.resource(uri)
        return res

    def has_sub_registers(self, register):
        for subreg in register[REG.subregister]:
            return True
        return False

    def get_sub_registers(self, register):
        for subreg in register[REG.subregister]:
            yield self.get_resource(subreg.identifier)

    def has_member_items(self, register):
        # If a register has member items, it returns one
        member_generator = self.get_member_items(register, resolve=False)
        if member_generator:
            try:
                return member_generator.next()
            except StopIteration:
                return False
        return False

    def get_member_items(self, register, resolve=True):
        # Members may be expressed with rdfs:isDefinedBy (
        for subj, obj in self.graph.subject_objects(RDFS.isDefinedBy):
            if obj == register:
                yield self.get_resource(subj.identifier, resolve=resolve)
        # Members may also be found as skos:member but not subregister (e.g. WMO)
        subregisters = set(subreg.identifier for subreg in register[REG.subregister])
        for member in register[SKOS.member]:
            if member.identifier not in subregisters:
                yield self.get_resource(member.identifier, resolve=resolve)
        # Members may be rdfs:member
        # e.g. http://codes.wmo.int/system/prefixes?_format=ttl

    def get_resource_types(self, resource):
        return [str(type_.identifier).split('#')[1]
                for type_ in resource[RDF.type]]

    def should_harvest_resource(self, resource):
        # Harvest if it contains a member item (not expecting sub-registers)
        # i.e. Don't harvest if it has sub-registers or no member itms
        has_no_sub_reg = not self.has_sub_registers(resource)
        a_member = self.has_member_items(resource)
        if has_no_sub_reg and not a_member:
            print '           No sub registers'
            return False
        if not has_no_sub_reg and a_member:
            print '!          Sub registers and member: ', a_member[RDFS.label].next()
            return True
        if has_no_sub_reg and a_member:
            print '           Member and no sub registers: ', a_member[RDFS.label].next()
            return True
        return False

    def get_harvestable_resources(self):
       return self._get_harvestable_resources(self.get_resource(self.top_level_uri), 0)

    def _get_harvestable_resources(self, start_resource, recurses):
        print '%s %s' % (' ' * recurses, start_resource)
        if self.should_harvest_resource(start_resource):
            yield start_resource
        else:
            for subres in self.get_sub_registers(start_resource):
                if '/system/' in subres.identifier:
                    print 'Skipping system register: ', subres.identifier
                    continue
                for res in self._get_harvestable_resources(subres, recurses+1):
                    yield res

top_uri = 'http://environment.data.gov.uk/registry/def'
#top_uri = 'http://codes.wmo.int/'
#top_uri = 'http://codes.wmo.int/49-2'
ldr = LinkedDataRegistry(top_uri)
res = ldr.get_resource(top_uri)
sr = [sr for sr in ldr.get_sub_registers(res)][0]
ldr.get_resource(sr.identifier)
for res_ in ldr.get_harvestable_resources(): print '           Harvest: ', res_.identifier, res_[RDFS.label].next()
