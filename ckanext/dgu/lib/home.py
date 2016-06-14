import lxml.html
import requests
from beaker.cache import cache_region

log = __import__('logging').getLogger(__name__)

blog_feed_url = 'https://data.blog.gov.uk/feed/atom/'


@cache_region('short_term', 'blog_posts')
def get_latest_blog_posts():
    log.debug('Requesting blog posts: %s', blog_feed_url)
    try:
        # verify=False because occasionally we've received an obscure error:
        # TypeError("initializer for ctype 'int(*)(int, X509_STORE_CTX *)'
        # appears indeed to be 'int(*)(int, X509_STORE_CTX *)', but the types
        # are different (check that you are not e.g. mixing up different ffi
        # instances)",)
        response = requests.get(blog_feed_url, verify=False)
        # although the first line of the XML declares it is already utf8
        # encoded, it contains unicode chars...
        feed_str = response.text.encode('utf8')
        blogs = _get_blog_info(feed_str)
    except Exception, e:
        log.error('Exception getting blog posts: %s', e)
        blogs = []
    log.debug('Blog posts: %s', blogs)
    return blogs


def _get_blog_info(feed_str):
    '''Returns the first 3 blog posts'''
    # use lxml.etree instead of lxml.html because although you have to deal
    # with namespaces, and it is strict about closing tags, it does recognize
    # cname text in the title, which lxml.html seems to miss
    blogs = []
    tree = lxml.etree.fromstring(feed_str)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    count = 0
    for entry_node in tree.xpath('//atom:entry', namespaces=ns):
        title = entry_node.xpath('./atom:title/text()', namespaces=ns)[0]
        url = entry_node.xpath('./atom:link/@href', namespaces=ns)[0]
        category = entry_node.xpath('./atom:category/@term', namespaces=ns)[0]
        if category != 'Open Data':
            continue
        content = entry_node.xpath('./atom:content/text()', namespaces=ns)[0]
        content_tree = lxml.html.fromstring(content)
        img_urls = content_tree.xpath('.//img/@src', namespaces=ns)
        img_url = img_urls[0] if img_urls else None
        blogs.append((title, url, img_url))
        count += 1
        if count >= 3:
            break
    return blogs
