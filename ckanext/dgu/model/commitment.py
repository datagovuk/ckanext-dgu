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

class Commitment(Base):
    """
    """
    __tablename__ = 'commitment'

    id = Column(types.UnicodeText,
           primary_key=True,
           default=make_uuid)

    created   = Column(types.DateTime, default=datetime.now)

    source = Column(types.UnicodeText, nullable=False, index=True)
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