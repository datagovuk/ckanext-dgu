import StringIO

class PublisherNode:
    """
    A tree node for rendering publishers in our hierarchy view
    """

    def __init__(self,sl, s, root_url):
        self.title = s
        self.slug = sl
        self.children = []
        self.root_url = root_url or 'publisher'

    def indent(self,x, txt):
        return ('   ' * x) + txt

    def linkify(self):
        # Should use
        # h.url_for(controller='ckanext.dgu.controllers.publisher:PublisherController', action='read', id=self.slug)
        return "<a href='/%s/%s'>%s</a>" % (self.root_url, self.slug,self.title)

    def render(self):
        """
        Renders the output from this tree as a string
        """
        output = StringIO.StringIO()
        self.format_output( output=output, lvl=0 )
        contents = output.getvalue()
        output.close()
        return contents

    def format_output(self, output, lvl=0, ):
        """
        Formats the tree in a format that is useful for rendering to
        jstree.
        """
        output.write( self.indent(lvl,'<ul>') )
        for nx in self.children:
            output.write( self.indent(lvl, "<li id='node_" + nx.slug + "'>" + nx.linkify())   )
            if len(nx.children) > 0 and nx.slug != self.slug:
                nx.format_output( output, lvl+1)
            output.write( self.indent(lvl, "</li>") )
        output.write( self.indent(lvl,'</ul>') )
