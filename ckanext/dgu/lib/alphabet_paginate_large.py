'''
Based on alphabet_paginate, but only queries the current page - not 
items for all the letters of the alphabet. This makes it more efficient for
large databases, but doesn\'t disable links to letters that have no results.
'''
from itertools import dropwhile
import re
from sqlalchemy import  __version__ as sqav
from sqlalchemy.orm.query import Query
from pylons.i18n import _
from webhelpers.html.builder import HTML
from routes import url_for

from ckan.lib.alphabet_paginate import AlphaPage

class AlphaPageLarge(AlphaPage):
    def __init__(self, collection, alpha_attribute, page, other_text, paging_threshold=50,
                controller_name='tag'):
        '''
        @param collection - liist or sqlalchemy query of the items to paginate.
        @param alpha_attribute - name of the attribute (on each item of the
                             collection) which has the string to paginate by
        @param page - the page identifier - the start character or other_text
        @param other_text - the (i18n-ized) string for items with
                            non-alphabetic first character.
        @param paging_threshold - the minimum number of items required to
                              start paginating them.
        @param controller_name - The name of the controller that will be linked to,
                            which defaults to tag.  The controller name should be the
                            same as the route so for some this will be the full
                            controller name such as 'A.B.controllers.C:ClassName'
        '''
        self.collection = collection
        self.alpha_attribute = alpha_attribute
        self.page = page
        self.other_text = other_text
        self.paging_threshold = paging_threshold
        self.controller_name = controller_name

        self.letters = [char for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'] + [self.other_text]
        
    def pager(self, q=None):
        '''Returns pager html - for navigating between the pages.
           e.g. Something like this:
             <ul class='pagination pagination-alphabet'>
                 <li class="active"><a href="/package/list?page=A">A</a></li>
                 <li><a href="/package/list?page=B">B</a></li>
                 <li><a href="/package/list?page=C">C</a></li>
                    ...
                 <li class="disabled"><a href="/package/list?page=Z">Z</a></li>
                 <li><a href="/package/list?page=Other">Other</a></li>
             </ul>
        '''
        if self.item_count < self.paging_threshold:
            return ''
        pages = []
        page = q or self.page
        for letter in self.letters:
            href = url_for(controller=self.controller_name, action='index', page=letter)
            link = HTML.a(href=href, c=letter)
            if letter != page:
                li_class = ''
            else:
                li_class = 'active'
            attributes = {'class_': li_class} if li_class else {}
            page_element = HTML.li(link, **attributes)
            pages.append(page_element)
        ul = HTML.tag('ul', *pages)
        div = HTML.div(ul, class_='pagination pagination-alphabet')
        return div
