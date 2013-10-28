import re
import uuid
from datetime import datetime

from sqlalchemy import Table, Column, MetaData, ForeignKey
from sqlalchemy import types, orm
from sqlalchemy.sql import select
from sqlalchemy.orm import mapper, relationship
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base

import ckan.model as model
from ckan.lib.base import *

from ckan.model.group import group_table

log = __import__('logging').getLogger(__name__)

Base = declarative_base()

def make_uuid():
    return unicode(uuid.uuid4())

metadata = MetaData()


ODS_LINKS = {
    "DECC":"http://data.gov.uk/library/decc-open-data-strategy",
    "DEFRA":"http://data.gov.uk/library/defras-open-data-strategy",
    "DWP": "http://data.gov.uk/library/dwp-open-data-strategy",
    "HMRC": "http://data.gov.uk/library/hmrc-open-data-strategy",
    "BIS": "http://data.gov.uk/library/bis-open-data-strategy",
    "DfE": "http://data.gov.uk/library/dfe-open-data-strategy",
    "DFID": "http://data.gov.uk/library/dfid-open-data-strategy",
    #"FCO": "http://data.gov.uk/library/fco-open-data-strategy",
    "MOD": "http://data.gov.uk/library/mod-open-data-strategy",
    "DCMS": "http://data.gov.uk/library/dcms-open-data-strategy",
    "DfT": "http://data.gov.uk/library/dft-open-data-strategy",
    "CO": "http://data.gov.uk/library/cabinet-office-open-data-strategy",
    "DCLG": "http://data.gov.uk/library/dclg-open-data-strategy",
    "HMT": "http://data.gov.uk/library/hmt-open-data-strategy",
    "HO": "http://data.gov.uk/library/home-office-open-data-strategy",
    "DoH": "http://data.gov.uk/library/dh-open-data-strategy",
    "FCO": "http://data.gov.uk/library/fco-open-data-strategy-refresh",
}

ODS_ORGS = {
    "DECC":"department-of-energy-and-climate-change",
    "DEFRA":"department-for-environment-food-and-rural-affairs",
    "DWP": "department-for-work-and-pensions",
    "HMRC": "her-majestys-revenue-and-customs",
    "BIS": "department-for-business-innovation-and-skills",
    "DfE": "department-for-education",
    "DFID": "department-for-international-development",
    "MOD": "ministry-of-defence",
    "DCMS": "department-for-culture-media-and-sport",
    "DfT": "department-for-transport",
    "CO": "cabinet-office",
    "DCLG": "department-for-communities-and-local-government",
    "HMT": "her-majestys-treasury",
    "HO": "home-office",
    "DoH": "department-of-health",
    "FCO": "foreign-and-commonwealth-office",
}

class Commitment(Base):
    """
    A commitment that it either from an Open Data Strategy or one of
    the PMs letters.
    """
    __tablename__ = 'commitment'

    id = Column(types.UnicodeText,
           primary_key=True,
           default=make_uuid)

    created   = Column(types.DateTime, default=datetime.now)

    source = Column(types.UnicodeText, nullable=False, index=True)
    dataset_name = Column(types.UnicodeText, nullable=False, index=True)
    commitment_text = Column(types.UnicodeText, nullable=False, index=True)
    notes = Column(types.UnicodeText, nullable=False, index=True)
    dataset = Column(types.UnicodeText, nullable=False, index=True)
    publisher = Column(types.UnicodeText, nullable=False, index=True)
    author = Column(types.UnicodeText, nullable=False, index=True)
    state = Column(types.UnicodeText, nullable=False, index=True)

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get(cls, id):
        return model.Session.query(cls).filter(cls.id==id).first()

    @classmethod
    def get_for_publisher(cls, id):
        return model.Session.query(cls).filter(cls.publisher==id)

def init_tables(e):
    Base.metadata.create_all(e)