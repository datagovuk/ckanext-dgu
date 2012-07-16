import re
import pylons

class ResourceFormats(object):
    formats = None
    canonised_formats = None

    @classmethod
    def init_formats(cls):
        cls.formats =  pylons.config.get('dgu.resource_formats', '').split()

    @classmethod
    def init_canonised_formats(cls):
        cls.canonised_formats = [cls.canonise(fmt) for fmt in cls.formats]

    @classmethod
    def match(cls, raw_resource_format):
        '''For a given resource format, see what matches relatively closely from
        the list of 'good' formats. Returns the best match or None.'''
        # Try exact match
        if not cls.formats:
            cls.init_formats()
        if raw_resource_format in cls.formats:
            return raw_resource_format

        # Try canonised match
        canonised_raw = cls.canonise(raw_resource_format)
        if not cls.canonised_formats:
            cls.init_canonised_formats()
        if canonised_raw in cls.canonised_formats:
            return cls.formats[cls.canonised_formats.index(canonised_raw)]

    @classmethod
    def get_all(cls):
        '''Returns a list of the 'good' formats.'''
        if not cls.formats:
            cls.init_formats()
        return cls.formats

    @classmethod
    def canonise(cls, format_):
        return re.sub('[^a-z/+]', '', cls.tidy(format_).lower())

    @classmethod
    def tidy(cls, format_):
        return format_.strip().lstrip('.')

match = ResourceFormats.match
get_all = ResourceFormats.get_all
