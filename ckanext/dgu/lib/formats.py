'''A directory of file formats and their properties'''

class Formats(object):
    @classmethod
    def by_display_name(cls):
        '''Returns the formats data as a dict keyed by the display name'''
        if not hasattr(cls, '_by_display_name'):
            data = cls.get_data()
            cls._by_display_name = {}
            for format_dict in data:
                cls._by_display_name[format_dict['display_name']] = format_dict
        return cls._by_display_name

    @classmethod
    def by_mime_type(cls):
        '''Returns the formats data as a dict keyed by mime type'''
        if not hasattr(cls, '_by_mime_type'):
            data = cls.get_data()
            cls._by_mime_type = {}
            for format_dict in data:
                for mime_type in format_dict['mime_types']:
                    cls._by_mime_type[mime_type] = format_dict
        return cls._by_mime_type

    @classmethod
    def by_extension(cls):
        '''Returns the formats data as a dict keyed by mime type'''
        if not hasattr(cls, '_by_extension'):
            data = cls.get_data()
            cls._by_extension = {}
            for format_dict in data:
                for extension in format_dict['extensions']:
                    cls._by_extension[extension] = format_dict
        return cls._by_extension

    @classmethod
    def get_data(cls):
        '''Returns the list of data formats, each one as a dict

        e.g. [{'display_name': 'TXT', 'extensions': ('txt',), 'extension': 'txt',
               'mime_types': ('text/plain',), 'openness': 1},
              ...]
        '''
        if not hasattr(cls, '_data'):
            # store the data here so it only loads when first used, rather
            # than on module load
            data_flat = (
                # Display name, extensions (lower case), mime-types, openness
                ('TXT', ('txt',), ('text/plain',), 1),
                ('TXT / Zip', ('txt.zip',), (), 1),
                ('HTML', ('html', 'htm',), ('text/html',), 1),
                ('PDF', ('pdf',), ('application/pdf',), 1),
                ('PDF / Zip', ('pdf.zip',), (), 1),
                ('Zip', ('zip',), ('application/x-zip', 'application/x-compressed', 'application/x-zip-compressed', 'application/zip', 'multipart/x-zip'), 1),
                ('Torrent', ('torrent',), ('application/x-bittorrent',), 1),
                ('DOC', ('doc', 'docx'), ('application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-word.document.macroEnabled.12'), 1),
                ('PPT', ('ppt', 'pptx'), ('application/mspowerpoint', 'application/vnd.ms-powerpoint.presentation.macroEnabled.12'), 1),
                ('XLS', ('xls', 'xlsx'), ('application/excel', 'application/x-excel', 'application/x-msexcel', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel.sheet.binary.macroenabled.12', 'application/vnd.ms-excel.sheet.macroenabled.12', 'application/vnd.msexcel'), 2),
                ('XLS / Zip', ('xls.zip',), (), 2),
                ('SHP', ('shp',), (), 2),
                ('SHP / Zip', ('shp.zip',), (), 2),
                ('CSV', ('csv',), ('text/csv','text/comma-separated-values'), 3),
                ('CSV / Zip', ('csv.zip',), (), 3),
                ('PSV', ('psv',), ('text/psv','text/pipe-separated-values'), 3),
                ('PSV / Zip', ('psv.zip',), (), 3),                
                ('JSON', ('json',), ('application/json', 'text/x-json'), 3),
                ('XML', ('xml',), ('text/xml',), 3),
                ('XML / Zip', ('xml.zip',), (), 3),
                ('RSS', ('rss',), ('text/rss+xml',), 3),
                ('ODS', ('ods',), ('application/vnd.oasis.opendocument.spreadsheet',), 3),
                ('WMS', ('wms',), ('application/vnd.ogc.wms_xml',), 3),
                ('KML', ('kml',), ('application/vnd.google-earth.kml+xml',), 3),
                ('NetCDF', ('cdf', 'netcdf'), ('application/x-netcdf',), 3),
                ('RDF/XML', ('rdf',), ('application/rdf+xml',), 4),
                ('RDFa', (), (), 4),
                )
            cls._data = []
            for line in data_flat:
                display_name, extensions, mime_types, openness = line
                format_dict = dict(zip(('display_name', 'extensions', 'mime_types', 'openness'), line))
                format_dict['extension'] = extensions[0] if extensions else ''
                cls._data.append(format_dict)
        return cls._data

# Mime types which give not much clue to the format
VAGUE_MIME_TYPES = set(('application/octet-stream',))
