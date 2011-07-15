import re

from genshi.filters.transform import Transformer
from genshi.input import HTML

from ckan.model import Session
from ckanext.harvest.model import HarvestObject
import ckanext.dgu.forms.html as html

def harvest_filter(stream, pkg):
    # We need the guid from the HarvestedObject!
    doc = Session.query(HarvestObject). \
          filter(HarvestObject.package_id==pkg.id). \
          order_by(HarvestObject.metadata_modified_date.desc()). \
          order_by(HarvestObject.gathered.desc()). \
          limit(1).first()
    if doc:
        data = {'guid': doc.guid}
        html_code = html.GEMINI_CODE
        if len(pkg.resources) == 0:
            # If no resources, the table has only two columns
            html_code = html_code.replace('<td></td>','')

        stream = stream | Transformer('body//div[@class="resources subsection"]/table')\
            .append(HTML(html_code % data))
    return stream

