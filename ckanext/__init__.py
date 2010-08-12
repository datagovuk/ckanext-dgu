# Put dgu/ckanext into the ckanext namespace of the actual ckanext module
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)
