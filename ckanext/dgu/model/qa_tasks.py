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
    is_broken = Column(types.Boolean)
    archiver_status = Column(types.UnicodeText)
    created   = Column(types.DateTime, default=datetime.now)

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def create(cls, entity):
        from paste.deploy.converters import asbool

        c = cls()
        c.created = entity.last_updated
        c.resource_id = entity.entity_id
        c.created = entity.last_updated

        # We need to find the dataset_id for the resource.
        q = """
            SELECT P.id from package P
            INNER JOIN resource_group RG ON RG.package_id = P.id
            INNER JOIN resource R ON R.resource_group_id = RG.id
            WHERE R.id = '%s';
        """
        row = model.Session.execute(q % c.resource_id).first()
        if row:
            c.dataset_id = row[0]
        else:
            # If there is no row, we can't add the dataset. This may be
            # that the resource no longer exists.
            c.dataset_id = ''

        c.openness_score = int(entity.value)

        if entity.error:
            d = json.loads(entity.error)
            c.is_broken = asbool(d.get('is_broken', False))
            c.format = d.get('format')
            c.archiver_status = d.get('archiver_status')
            c.openness_score_reason = d.get('reason')

        return c

def init_tables(e):
    Base.metadata.create_all(e)
