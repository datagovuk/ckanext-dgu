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

from ckan.model.package import package_table

log = __import__('logging').getLogger(__name__)

Base = declarative_base()

def make_uuid():
    return unicode(uuid.uuid4())

metadata = MetaData()

class Feedback(Base):
    """
    """
    __tablename__ = 'feedback'

    id = Column(types.UnicodeText,
           primary_key=True,
           default=make_uuid)
    created   = Column(types.DateTime, default=datetime.now)
    economic  = Column(types.Boolean)
    social    = Column(types.Boolean)
    effective = Column(types.Boolean)
    other     = Column(types.Boolean)
    linked    = Column(types.Boolean)

    economic_comment  = Column(types.UnicodeText)
    social_comment    = Column(types.UnicodeText)
    effective_comment = Column(types.UnicodeText)
    other_comment     = Column(types.UnicodeText)
    linked_comment    = Column(types.UnicodeText)

    responding_as = Column(types.UnicodeText)
    organisation  = Column(types.UnicodeText)
    organisation_name  = Column(types.UnicodeText)

    contact = Column(types.Boolean)

    moderated = Column(types.Boolean, default=False)
    moderation_required = Column(types.Boolean, default=False)
    moderated_by = Column(types.UnicodeText, nullable=True)

    # Used for scoring as spam. If mollom tells us it is high, and then it gets flagged
    # we can use this to determine whether to auto delete instead.
    spam_score = Column(types.Integer, default=0)

    package_id = Column(types.UnicodeText, nullable=False, index=True)
    user_id = Column(types.UnicodeText, nullable=False, index=True)
    is_publisher  = Column(types.Boolean, default=False)

    visible  = Column(types.Boolean, default=True)

    active  = Column(types.Boolean, default=True)

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get(cls, id):
        return model.Session.query(cls).filter(cls.id==id).first()

    @classmethod
    def users_count(cls, pkg):
        return model.Session.query(cls).filter(cls.package_id==pkg['id']).\
            filter(cls.visible==True).filter(cls.active==True).distinct('user_id').count()

    @classmethod
    def comments_count(cls, pkg):
        total = 0
        for comment in model.Session.query(cls).filter(cls.package_id==pkg['id']).\
                filter(cls.active==True).filter(cls.visible==True):
            if comment.economic:
                total += 1
            if comment.social:
                total += 1
            if comment.effective:
                total += 1
            if comment.other:
                total += 1
            if comment.linked:
                total += 1
        return total

    def __str__(self):
        return u"<Feedback: %s, vis:%s, act:%s>" % (self.user_id, self.visible, self.active)

    def __repr__(self):
        return u"<Feedback: %s, vis:%s, act:%s>" % (self.user_id, self.visible, self.active)


class FeedbackBlockedUser(Base):
    """
    """
    __tablename__ = 'feedback_blocked'

    id = Column(types.UnicodeText,
           primary_key=True,
           default=make_uuid)
    created   = Column(types.DateTime, default=datetime.now)

    # The blocked user
    user_id  = Column(types.UnicodeText, index=True)

    # Who blocked this user
    blocked_by  = Column(types.UnicodeText)

    # The ID of the feedback that triggered this ban
    feedback_id = Column(types.UnicodeText)


    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def is_user_blocked(cls, user_id):
        return model.Session.query(cls).filter(cls.user_id==user_id).count() > 0


def init_tables(e):
    Base.metadata.create_all(e)