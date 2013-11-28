import uuid
from datetime import datetime

from sqlalchemy import Column, MetaData
from sqlalchemy import types
from sqlalchemy.orm import mapper
from sqlalchemy.ext.declarative import declarative_base

import ckan.model as model
from ckan.lib.base import *

log = __import__('logging').getLogger(__name__)

Base = declarative_base()

def make_uuid():
    return unicode(uuid.uuid4())

metadata = MetaData()

class QATask(Base):
    """
    Contains the latest results per dataset/resource for QA tasks
    run against them.
    """
    __tablename__ = 'qa_task'

    id = Column(types.UnicodeText, primary_key=True, default=make_uuid)
    dataset_id = Column(types.UnicodeText, nullable=False, index=True)
    resource_id = Column(types.UnicodeText, nullable=False, index=True)
    error = Column(types.UnicodeText)

    openness_score = Column(types.Integer)
    openness_score_reason = Column(types.UnicodeText)

    url = Column(types.UnicodeText)
    format = Column(types.UnicodeText)
    is_broken = openness_score_reason = Column(types.Boolean)
    created   = Column(types.DateTime, default=datetime.now)

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def create(cls, entity):
        c = cls()
        c.created = entity.last_updated

        # unpack the error json
        return c



def init_tables(e):
    Base.metadata.create_all(e)