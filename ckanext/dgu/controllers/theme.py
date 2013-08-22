"""
The ThemeController is used for grouping datasets by theme, using the 
theme-primary extra that is set on *some* datasets.  This is now a 
requirement and so over time all datasets will eventually have a theme 
attached.

Themes are not currently stored in the database (they're in schema.py for now
but should the need arise to add more 
"""
import sqlalchemy
import pylons
import os
import logging
from ckan.lib.base import (BaseController, abort)
from ckanext.dgu.plugins_toolkit import (c, render, get_action)
from ckanext.dgu.schema import THEMES
from ckan import model

log = logging.getLogger(__name__)


class ThemeController(BaseController):

    def index(self):
        return render('themed/index.html')

    def named_theme(self, name):
        """ 
        Shows the theme home page for a specified theme containing information relevant 
        to *just* that theme, popular and new datasets as well as recent apps+ideas from 
        the front end.
        """
        raise NotImplementedError('Cannot view theme pages yet.')
        c.theme = name
        c.theme_name = THEMES.get(name)
        if not c.theme_name:
            abort(404)

        c.dataset_count = model.Session.query(model.Package)\
            .join(model.PackageExtra)\
            .filter(model.PackageExtra.key=='theme-primary')\
            .filter(model.PackageExtra.value==c.theme_name)\
            .filter(model.Package.state=='active').count()

        c.latest = self._search(theme=c.theme_name)
        c.popular = self._search(theme=c.theme_name, sort_string='popularity asc')

        return render('themed/theme.html')

    def _search(self, theme='', q='', rows=5, sort_string='last_major_modification desc'):
        """
        Helper for retrieving just a handful of popular/recent datasets for the 
        current theme. 
        """
        raise NotImplementedError('Cannot view theme pages yet.')
        from ckan.lib.search import SearchError
        packages = []
        try:
            # package search
            context = {'model': model, 'session': model.Session, 'user': 'visitor'}
            data_dict = {
                'q': q,
                'fq': 'theme-primary:"%s"' % theme,
                'facet':'true',
                'rows': rows,
                'start':0,
                'sort': sort_string,
            }
            query = get_action('package_search')(context, data_dict)
            packages = query['results']
        except SearchError, se:
            log.error('Search error: %s', se)

        return packages
