from curate.actions import Action
from datetime import datetime

class report(Action):
    def __call__(self, tNode, inferredTriple, token, _binding, debug = False):
        dataset = self.get(self.sbind, token)
        resource = self.get(self.obind, token)

        q = """
        PREFIX http: <http://www.w3.org/2006/http#>
        SELECT DISTINCT ?code WHERE {
            ?req http:requestURI %(resource)s .
            ?req http:resp ?resp .
            ?resp http:statusCodeNumber ?code
        }
        """ % { "resource": resource.n3() }
        code = ""
        comment = ""
        try:
            for code in tNode.network.inferredFacts.query(q):
                break
        except:
            pass
        
        q = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX http: <http://www.w3.org/2006/http#>
        PREFIX curl: <http://eris.okfn.org/ww/2010/12/curl#>
        SELECT DISTINCT ?comment WHERE {
            { ?req http:requestURI %(resource)s .
              ?req http:resp ?resp .
              ?resp rdfs:comment ?comment } UNION
            { ?curl curl:uri %(resource)s .
              ?curl rdfs:comment ?comment }
        }
        """ % { "resource": resource.n3() }
        try:
            for comment in tNode.network.inferredFacts.query(q):
                break
        except:
            comment = "Possibly bad URI: %s" % resource.n3()

        def recode(s):
            try:
                s = s.encode("utf-8")
            except UnicodeEncodeError:
                s = s.encode("latin1")
            return s.decode("utf-8")

        timestamp = unicode(datetime.utcnow())
        print u",".join(recode(x) for x  in (timestamp, dataset, resource, code, comment)).encode("utf-8")
