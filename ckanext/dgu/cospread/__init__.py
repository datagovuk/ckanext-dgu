from ckanext.api_command import ApiCommand
from ckanext.dgu.cospread.cospread import CospreadImporter
from ckanext.dgu.cospread.loader import CospreadLoader
from ckanclient import CkanClient

class CospreadCommand(ApiCommand):
    def __init__(self):
        usage = 'usage: %prog [options] {metadata.xls}'
        super(CospreadCommand, self).__init__(usage=usage)

    def add_options(self):
        self.parser.add_option("-t", "--include-given-tags",
                               dest="include_given_tags",
                               action="store_true",
                               default=False,
                               help="Uses source's tags (in addition to just common keywords found.)")

    def command(self):
        super(CospreadCommand, self).command()

        if len(self.args) != 1:
            self.parser.error('You must specify metadata file')
        else:
            data_filepath = self.args[0]
        importer = CospreadImporter(filepath=data_filepath,
                                    include_given_tags=self.options.include_given_tags)
        
        loader = CospreadLoader(self.client)
        loader.load_packages(importer.pkg_dict())

def load():
    CospreadCommand().command()
