import uuid

from sqlalchemy import Column
from sqlalchemy import types
from sqlalchemy.ext.declarative import declarative_base

from ckan import model

DeclarativeBase = declarative_base()


def make_uuid():
    return unicode(uuid.uuid4())


class Schema(DeclarativeBase, model.DomainObject):
    """
    A data schema/vocabulary/ontology that describes the structure/types in
    data.
    """
    __tablename__ = 'schema'

    id = Column(types.UnicodeText,
                primary_key=True,
                default=make_uuid)

    url = Column(types.UnicodeText, nullable=False, index=True)
    title = Column(types.UnicodeText, nullable=False, index=True)

    @classmethod
    def get(cls, id):
        return model.Session.query(cls).filter(cls.id==id).first()

    @classmethod
    def by_title(cls, title, autoflush=True):
        obj = model.Session.query(cls).autoflush(autoflush)\
                   .filter_by(title=title).first()
        return obj

    @classmethod
    def by_url(cls, url):
        return model.Session.query(cls).filter(cls.url==url).first()


class Codelist(DeclarativeBase, model.DomainObject):
    """
    A code list defines a set of values to be used in a field of a dataset.
    """
    __tablename__ = 'codelist'

    id = Column(types.UnicodeText,
                primary_key=True,
                default=make_uuid)

    url = Column(types.UnicodeText, nullable=False, index=True)
    title = Column(types.UnicodeText, nullable=False, index=True)

    @classmethod
    def get(cls, id):
        return model.Session.query(cls).filter(cls.id==id).first()

    @classmethod
    def by_title(cls, title, autoflush=True):
        obj = model.Session.query(cls).autoflush(autoflush)\
                   .filter_by(title=title).first()
        return obj

    @classmethod
    def by_url(cls, url):
        return model.Session.query(cls).filter(cls.url==url).first()


def init_tables(e):
    DeclarativeBase.metadata.create_all(e)
