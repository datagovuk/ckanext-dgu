import sqlalchemy
from beaker.cache import cache_region

from ckan import model
from ckanext.dgu.plugins_toolkit import get_action

log = __import__('logging').getLogger(__name__)


@cache_region('short_term', 'themes')
def get_themes():
    '''
    Get the themes from ckanext-taxonomy
    '''
    context = {'model': model}
    try:
        log.debug('Refreshing home page themes')
        terms = get_action('taxonomy_term_list')(
            context, {'name': 'dgu-themes'})
    except sqlalchemy.exc.OperationalError, e:
        if 'no such table: taxonomy' in str(e):
            model.Session.remove()  # clear the erroring transaction
            raise ImportError('ckanext-taxonomy tables not setup')
        raise
    return [(t['label'], t['description']) for t in terms]
