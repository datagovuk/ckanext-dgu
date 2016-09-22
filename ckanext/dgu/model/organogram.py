import uuid
from datetime import datetime

from sqlalchemy import Column, MetaData
from sqlalchemy import types
from sqlalchemy.ext.declarative import declarative_base

import ckan.model as model

log = __import__('logging').getLogger(__name__)

Base = declarative_base()

def make_uuid():
    return unicode(uuid.uuid4())

metadata = MetaData()


class Organogram(Base):
    """
    Organogram data for a particular public body and snapshot date.
    """
    __tablename__ = 'organogram'

    id = Column(types.UnicodeText, primary_key=True, default=make_uuid)

    publisher_id = Column(types.UnicodeText, nullable=False, index=True)
    date = Column(types.DateTime, nullable=False, index=True)  # i.e. version
    original_xls_filepath = Column(types.UnicodeText, nullable=True, index=True)  # where it was stored on tso or the upload filename
    xls_filepath = Column(types.UnicodeText, nullable=False, index=True)  # where we store it, relative to organogram dir
    csv_senior_filepath = Column(types.UnicodeText, nullable=True) # where we store it, relative to organogram dir
    csv_junior_filepath = Column(types.UnicodeText, nullable=True) # where we store it, relative to organogram dir

    upload_user = Column(types.UnicodeText, nullable=False)  # user_id or string for legacy
    upload_date = Column(types.DateTime, nullable=True, default=datetime.now)
    signoff_user = Column(types.UnicodeText, nullable=True)
    signoff_date = Column(types.DateTime, nullable=True)
    publish_user = Column(types.UnicodeText, nullable=True)
    publish_date = Column(types.DateTime, nullable=True)

    state = Column(types.UnicodeText, nullable=False, index=True) # uploaded/signed off/published

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get(cls, publisher_id, date):
        return model.Session.query(cls) \
            .filter(cls.publisher_id == publisher_id) \
            .filter(cls.date == date) \
            .first()

    @classmethod
    def get_by_publisher(cls, publisher_id):
        return model.Session.query(cls) \
            .filter(cls.publisher_id == publisher_id)

def init_tables(engine):
    Base.metadata.create_all(engine)