from sqlalchemy import Column, ForeignKey, types
from sqlalchemy.ext.declarative import declarative_base

import uuid
import datetime

Base = declarative_base()

def make_uuid():
    return unicode(uuid.uuid4())

class PublisherRequest(Base):
    __tablename__ = 'publisher_request'

    id = Column(types.UnicodeText,
           primary_key=True,
           default=make_uuid)

    #user_name = Column('user_name', types.UnicodeText, ForeignKey('ckan.user.name'), nullable=False)
    user_name = Column('user_name', types.UnicodeText, nullable=False)
    #group_name = Column('group_name', types.UnicodeText, ForeignKey('ckan.group.name'), nullable=False)
    group_name = Column('group_name', types.UnicodeText, nullable=False)
    date_of_request = Column('date_of_request', types.DateTime, default=datetime.datetime.utcnow, nullable=False)
    date_of_decision = Column('date_of_decision', types.DateTime, nullable=True)
    decision = Column('decision', types.Boolean, nullable=True)
    login_token = Column('login_token', types.UnicodeText, default=make_uuid, nullable=False)
    reason = Column('reason', types.UnicodeText)

def init_tables(e):
    Base.metadata.create_all(e)
