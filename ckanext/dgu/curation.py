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
        PREFIX rdfs: <http://www.w3.org/2006/http#>
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
        
        print ",".join(str(x) for x  in (datetime.utcnow(), dataset, resource, code, comment))
