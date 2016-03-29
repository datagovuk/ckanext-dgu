import logging
import re
import urllib2
import socket
import httplib
from lxml import etree
import traceback

from owslib import wms as owslib_wms

import ckan.plugins as p

log = logging.getLogger(__name__)


def is_id(id_string):
    '''Tells the client if the string looks like a revision id or not'''
    reg_ex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(reg_ex, id_string))


def process_resource(ckan_ini_filepath, resource_id, queue):
    #log = process_resource.get_logger()
    #load_config(ckan_ini_filepath)
    #register_translator()

    from ckan import model
    from pylons import config

    assert is_id(resource_id), resource_id
    context_ = {'model': model, 'ignore_auth': True, 'session': model.Session}
    resource = p.toolkit.get_action('resource_show')(context_, {'id': resource_id})

    # Check if the service is a view service
    is_wms = _is_wms(url)
    if is_wms:
        #resource['verified'] = True
        #resource['verified_date'] = datetime.now().isoformat()
        base_urls = _wms_base_urls(url)
        resource['wms_base_urls'] = ' '.join(base_urls)
        resource_format = 'WMS'


def _is_wms(url):
    '''Given a WMS URL this method returns whether it thinks it is a WMS
    server or not. It does it by making basic WMS requests.
    '''
    # Try WMS 1.3 as that is what INSPIRE expects
    is_wms = _try_wms_url(url, version='1.3')
    # First try using WMS 1.1.1 as that is very common
    if not is_wms:
        is_wms = _try_wms_url(url, version='1.1.1')
    log.debug('WMS check result: %s', is_wms)
    return is_wms


# Like owslib_wms.WMSCapabilitiesReader(version=version).capabilities_url only
# it deals with uppercase param keys too!
def wms_capabilities_url(url):
    qs = []
    if service_url.find('?') != -1:
        qs = cgi.parse_qsl(service_url.split('?')[1])

    params = [x[0] for x in qs]

    if 'service' not in params:
        qs.append(('service', 'WMS'))
    if 'request' not in params:
        qs.append(('request', 'GetCapabilities'))    
    if 'version' not in params:
        qs.append(('version', self.version))

    urlqs = urlencode(tuple(qs))
    return service_url.split('?')[0] + '?' + urlqs


def _try_wms_url(url, version='1.3'):
    # Here's a neat way to run this manually:
    # python -c "import logging; logging.basicConfig(level=logging.INFO); from ckanext.dgu.gemini_postprocess import _try_wms_url; print _try_wms_url('http://soilbio.nerc.ac.uk/datadiscovery/WebPage5.aspx')"
    import pdb; pdb.set_trace()
    try:
        capabilities_url = wms_capabilities_url(url)
        log.debug('WMS check url: %s', capabilities_url)
        try:
            res = urllib2.urlopen(capabilities_url, None, 10)
            xml = res.read()
        except urllib2.HTTPError, e:
            # e.g. http://aws2.caris.com/sfs/services/ows/download/feature/UKHO_TS_DS
            log.info('WMS check for %s failed due to HTTP error status "%s". Response body: %s', capabilities_url, e, e.read())
            return False
        except urllib2.URLError, e:
            log.info('WMS check for %s failed due to HTTP connection error "%s".', capabilities_url, e)
            return False
        except socket.timeout, e:
            log.info('WMS check for %s failed due to HTTP connection timeout error "%s".', capabilities_url, e)
            return False
        except socket.error, e:
            log.info('WMS check for %s failed due to HTTP socket connection error "%s".', capabilities_url, e)
            return False
        except httplib.HTTPException, e:
            log.info('WMS check for %s failed due to HTTP error "%s".', capabilities_url, e)
            return False
        if not xml.strip():
            log.info('WMS check for %s failed due to empty response')
            return False
        # owslib only supports reading WMS 1.1.1 (as of 10/2014)
        if version == '1.1.1':
            try:
                wms = owslib_wms.WebMapService(url, xml=xml)
            except AttributeError, e:
                # e.g. http://csw.data.gov.uk/geonetwork/srv/en/csw
                log.info('WMS check for %s failed due to GetCapabilities response not containing a required field', url)
                return False
            except etree.XMLSyntaxError, e:
                # e.g. http://www.ordnancesurvey.co.uk/oswebsite/xml/atom/
                log.info('WMS check for %s failed parsing the XML response: %s', url, e)
                return False
            except owslib_wms.ServiceException:
                # e.g. https://gatewaysecurity.ceh.ac.uk/wss/service/LCM2007_GB_25m_Raster/WSS
                log.info('WMS check for %s failed - OGC error message: %s', url, traceback.format_exc())
                return False
            except socket.timeout, e:
                # e.g. http://lichfielddc.maps.arcgis.com/apps/webappviewer/index.html?id=2be0619b59a5418c8c9d785c09504f57
                log.info('WMS check for %s failed due to HTTP connection timeout error "%s".', capabilities_url, e)
                return False
            except socket.error, e:
                log.info('WMS check for %s failed due to HTTP socket connection error "%s".', capabilities_url, e)
                return False
            is_wms = isinstance(wms.contents, dict) and wms.contents != {}
            return is_wms
        else:
            try:
                tree = etree.fromstring(xml)
            except etree.XMLSyntaxError, e:
                # e.g. http://www.ordnancesurvey.co.uk/oswebsite/xml/atom/
                log.info('WMS check for %s failed parsing the XML response: %s', url,  e)
                return False
            if tree.tag != '{http://www.opengis.net/wms}WMS_Capabilities':
                # e.g. https://gatewaysecurity.ceh.ac.uk/wss/service/LCM2007_GB_25m_Raster/WSS
                log.info('WMS check for %s failed as top tag is not wms:WMS_Capabilities, it was %s', url, tree.tag)
                return False
            # check based on https://github.com/geopython/OWSLib/blob/master/owslib/wms.py
            se = tree.find('ServiceException')
            if se:
                log.info('WMS check for %s failed as it contained a ServiceException: %s', url, str(se.text).strip())
                return False
            return True
    except Exception, e:
        log.exception('WMS check for %s failed with uncaught exception: %s' % (url, str(e)))
    return False


def _wms_base_urls(url):
    '''Given a WMS URL this method returns the base URLs it uses. It does
    it by making basic WMS requests.
    '''
    # Here's a neat way to test this manually:
    # python -c "import logging; logging.basicConfig(level=logging.INFO); from ckanext.spatial.harvesters.gemini import GeminiSpatialHarvester; print GeminiSpatialHarvester._wms_base_urls('http://www.ordnancesurvey.co.uk/oswebsite/xml/atom/')"
    try:
        capabilities_url = wms_capabilities_url(url)
        # Get rid of the "version=1.1.1" param that OWSLIB adds, because
        # the OS WMS previewer doesn't specify a version, so may receive
        # later versions by default. And versions like 1.3 may have
        # different base URLs. It does mean that we can't use OWSLIB to parse
        # the result though.
        capabilities_url = re.sub('&version=[^&]+', '', capabilities_url)
        try:
            log.debug('WMS base url check: %s', capabilities_url)
            res = urllib2.urlopen(capabilities_url, None, 10)
            xml_str = res.read()
        except urllib2.HTTPError, e:
            # e.g. http://aws2.caris.com/sfs/services/ows/download/feature/UKHO_TS_DS
            log.info('WMS check for %s failed due to HTTP error status "%s". Response body: %s', capabilities_url, e, e.read())
            return False, set()
        except urllib2.URLError, e:
            log.info('WMS check for %s failed due to HTTP connection error "%s".', capabilities_url, e)
            return False, set()
        except socket.timeout, e:
            log.info('WMS check for %s failed due to HTTP connection timeout error "%s".', capabilities_url, e)
            return False, set()
        except socket.error, e:
            log.info('WMS check for %s failed due to HTTP connection socket error "%s".', capabilities_url, e)
            return False, set()
        except httplib.HTTPException, e:
            log.info('WMS check for %s failed due to HTTP error "%s".', capabilities_url, e)
            return False
        parser = etree.XMLParser(remove_blank_text=True)
        try:
            xml_tree = etree.fromstring(xml_str, parser=parser)
        except etree.XMLSyntaxError, e:
            # e.g. http://www.ordnancesurvey.co.uk/oswebsite/xml/atom/
            log.info('WMS base urls for %s failed parsing the XML response: %s', url, traceback.format_exc())
            return []
        # check it is a WMS
        if not 'wms' in str(xml_tree).lower():
            log.info('WMS base urls %s failed - XML top tag was not WMS response: %s', url, str(xml_tree))
            return []
        base_urls = set()
        namespaces = {'wms': 'http://www.opengis.net/wms', 'xlink': 'http://www.w3.org/1999/xlink'}
        xpath = '//wms:HTTP//wms:OnlineResource/@xlink:href'
        urls = xml_tree.xpath(xpath, namespaces=namespaces)
        for url in urls:
            if url:
                base_url = url.split('?')[0]
                base_urls.add(base_url)
        log.info('Extra WMS base urls: %r', base_urls)
        return base_urls
    except Exception, e:
        log.exception('WMS base url extraction %s failed with uncaught exception: %s' % (url, str(e)))
    return False
