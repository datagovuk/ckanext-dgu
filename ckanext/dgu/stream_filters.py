import re

from genshi.filters.transform import Transformer
from genshi.input import HTML

import ckanext.dgu.forms.html as html


def package_id_filter(stream, pkg):

    data = {'id': pkg.id}
    html_code = html.DATASET_ID_CODE

    stream = stream | Transformer('body//ul[@class="property-list"]')\
        .append(HTML(html_code % data))

    return stream

