import re

# Escape Lucene special characters: + - ! ( ) { } [ ] ^ " ~ * ? : \ /
# There are also operators && and ||, but we're just going to escape
# the individual ampersand and pipe chars.
# Also, we're not going to escape backslashes!
# http://lucene.apache.org/core/4_0_0/queryparser/org/apache/lucene/queryparser/classic/package-summary.html#Escaping%20Special%20Characters
ESCAPE_CHARS_RE = re.compile(r'(?<!\\)(?P<char>[&|+\-!(){}[\]^"~*?:/])')

def solr_escape(value):
    r"""Escape un-escaped special characters and return escaped value.

    >>> solr_escape(r'foo+') == r'foo\+'
    True
    >>> solr_escape(r'foo\+') == r'foo\+'
    True
    >>> solr_escape(r'foo\\+') == r'foo\\+'
    True
    """
    return ESCAPE_CHARS_RE.sub(r'\\\g<char>', value)
