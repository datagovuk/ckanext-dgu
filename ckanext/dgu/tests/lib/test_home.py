from nose.tools import assert_equal

from ckanext.dgu.lib.home import get_latest_blog_posts, _get_blog_info


class TestHome(object):
    def test_get_latest_blog_posts(self):
        # NB uses live server
        # Just check there are no exceptions
        posts = get_latest_blog_posts()
        assert_equal(len(posts), 3)
        for post in posts:
            print post

    def test_get_blog_info(self):
        posts = _get_blog_info(feed)
        assert posts == \
            [('What open government policy can learn from internet culture',
             'https://data.blog.gov.uk/2016/05/23/what-open-government-policy-can-learn-from-internet-culture/',
             'https://data.blog.gov.uk/wp-content/uploads/sites/164/2016/05/CiVXOvHXAAAJ-wC-310x175.jpg'
             )], posts

feed = '''<?xml version="1.0" encoding="UTF-8"?>
<feed
  xmlns="http://www.w3.org/2005/Atom"
  xmlns:thr="http://purl.org/syndication/thread/1.0"
  xml:lang="en-US"
  xml:base="https://data.blog.gov.uk/wp-atom.php"
   >
    <title type="text">Data in government</title>
    <subtitle type="text">News and updates on how the government works with data</subtitle>

    <updated>2016-05-31T10:25:28Z</updated>

    <link rel="alternate" type="text/html" href="https://data.blog.gov.uk" />
    <id>https://data.blog.gov.uk/feed/atom/</id>
    <link rel="self" type="application/atom+xml" href="https://data.blog.gov.uk/feed/atom/" />


    <entry>
        <author>
            <name>sophiebenger</name>
        </author>
        <title type="html"><![CDATA[What open government policy can learn from internet culture]]></title>
        <link rel="alternate" type="text/html" href="https://data.blog.gov.uk/2016/05/23/what-open-government-policy-can-learn-from-internet-culture/" />
        <id>https://data.blog.gov.uk/?p=14591</id>
        <updated>2016-05-23T11:59:43Z</updated>
        <published>2016-05-23T11:55:38Z</published>
        <category scheme="https://data.blog.gov.uk" term="Open Data" />     <summary type="html">
          <![CDATA[
            Last week saw the launch of the UK's 2016-18 Open Government National Action Plan - the third plan the government has produced as a member of the global Open Government Partnership.   The plan contains an impressive list of commitments, ...
            ]]>
          </summary>
        <content type="html" xml:base="https://data.blog.gov.uk/2016/05/23/what-open-government-policy-can-learn-from-internet-culture/">
          <![CDATA[
            <p><span style="font-weight: 400">Last week saw the launch...</span></p>
            <p><img class="alignnone size-medium wp-image-14593" src="https://data.blog.gov.uk/wp-content/uploads/sites/164/2016/05/CiVXOvHXAAAJ-wC-310x175.jpg" alt="CiVXOvHXAAAJ-wC" width="310" height="175" srcset="https://data.blog.gov.uk/wp-content/uploads/sites/164/2016/05/CiVXOvHXAAAJ-wC-310x175.jpg 310w, https://data.blog.gov.uk/wp-content/uploads/sites/164/2016/05/CiVXOvHXAAAJ-wC.jpg 600w" sizes="(max-width: 310px) 100vw, 310px" /></p>
          ]]>
        </content>
        <link rel="replies" type="text/html" href="https://data.blog.gov.uk/2016/05/23/what-open-government-policy-can-learn-from-internet-culture/#comments" thr:count="0"/>
        <link rel="replies" type="application/atom+xml" href="https://data.blog.gov.uk/2016/05/23/what-open-government-policy-can-learn-from-internet-culture/feed/atom/" thr:count="0"/>
        <thr:total>0</thr:total>
    </entry>
</feed>
'''