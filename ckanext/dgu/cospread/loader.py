from ckanext.loader import PackageLoader, ResourceSeries

class CospreadLoader(PackageLoader):
    def __init__(self, ckanclient):
        settings = ReplaceByName()
        super(CospreadLoader, self).__init__(ckanclient, settings)

