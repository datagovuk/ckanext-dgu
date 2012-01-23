import re

from genshi.filters.transform import Transformer
from genshi.input import HTML

from ckan.model import Session
from ckanext.harvest.model import HarvestObject
import ckanext.dgu.forms.html as html

def harvest_filter(stream, pkg):
    
    harvest_object_id = pkg.extras.get('harvest_object_id')
    if harvest_object_id:

        data = {'id': harvest_object_id}
        html_code = html.GEMINI_CODE
        if len(pkg.resources) == 0:
            # If no resources, the table has only two columns
            html_code = html_code.replace('<td></td>','')

        stream = stream | Transformer('body//div[@class="resources subsection"]')\
            .append(HTML(html_code % data))

    return stream

def package_id_filter(stream, pkg):

    data = {'id': pkg.id}
    html_code = html.DATASET_ID_CODE

    stream = stream | Transformer('body//ul[@class="property-list"]')\
        .append(HTML(html_code % data))

    return stream

