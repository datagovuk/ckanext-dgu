import xml.sax
import re
import os
import glob
import logging

import ckan.model as model
from loader import *

from sqlalchemy.util import OrderedDict

class OnsLoader(PackageLoader):
    def __init__(self, ckanclient):
        settings = ResourceSeries(
            field_keys_to_find_pkg_by=['title', 'department'],
            resource_id_prefix='hub/id/',
            field_keys_to_expect_invariant=[
                'update_frequency', 'geographical_granularity',
                'geographic_coverage', 'temporal_granularity',
                'precision', 'url', 'taxonomy_url', 'agency',
                'author', 'author_email', 'license_id'])
        super(OnsLoader, self).__init__(ckanclient, settings)
