from ckan.lib.base import BaseController, render
from ckan.lib.cache import proxy_cache

class CatalogueController(BaseController):
    @proxy_cache()
    def home(self):
        return render('catalogue/home.html')
