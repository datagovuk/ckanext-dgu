import logging
import datetime

from sqlalchemy import types, Table, Column, MetaData, ForeignKey, orm
from sqlalchemy.ext.declarative import declarative_base
from ckan import model

log = logging.getLogger(__name__)

__all__ = ['Collection', 'Publication', 'Attachment', 'init_tables']

# create table publications (id integer primary key, url text, title text);
# create table attachments (id integer primary key, url text, pub_id integer references publications(id), filename text);
# create table collections (id integer primary key, url text, title text);
# create table collection_publication (pub_id integer references publications(id), coll_id integer references collections(id), primary key (pub_id, coll_id))

metadata = MetaData()
Base = declarative_base()

class SimpleDomainObject(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def by_name(cls, name, autoflush=True):
        obj = model.Session.query(cls).autoflush(autoflush)\
                   .filter_by(name=name).first()
        return obj

    def __str__(self):
        return self.__unicode__().encode('utf8')

    def __unicode__(self):
        repr = u'<%s' % self.__class__.__name__
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            try:
                repr += u' %s=%s' % (col.name, getattr(self, col.name))
            except Exception, inst:
                repr += u' %s=%s' % (col.name, inst)
        return repr + '>'

    def __repr__(self):
        return self.__unicode__().encode('utf-8')


# A Publication can be in many Collections
# e.g. https://www.gov.uk/government/publications/nhs-foundation-trust-directory
collection_publication_table = Table(
    'collection_publication', Base.metadata,
    Column('id', types.UnicodeText, primary_key=True,
           default=model.types.make_uuid),
    Column('collection_id', types.UnicodeText, ForeignKey('collection.id')),
    Column('publication_id', types.UnicodeText, ForeignKey('publication.id')),
    Column('created', types.DateTime, default=datetime.datetime.now),
    )

publication_publink_table = Table(
    'publication_publink', metadata,
    Column('id', types.UnicodeText, primary_key=True,
           default=model.types.make_uuid),
    Column('publication_id', types.UnicodeText, ForeignKey('publication.id')),
    Column('publink_id', types.UnicodeText, ForeignKey('publink.id')),
    Column('created', types.DateTime, default=datetime.datetime.now),
    )


class GovukOrganization(Base, SimpleDomainObject):
    __tablename__ = 'govuk_organization'
    id = Column(types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    name = Column(types.UnicodeText, index=True)
    title = Column(types.UnicodeText, nullable=False)


class Collection(Base, SimpleDomainObject):
    __tablename__ = 'collection'
    id = Column(types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    name = Column(types.UnicodeText, index=True)
    url = Column(types.UnicodeText)
    title = Column(types.UnicodeText, nullable=False)
    summary = Column(types.UnicodeText)
    detail = Column(types.UnicodeText)
    govuk_organization_id = Column(types.UnicodeText,
                                   ForeignKey('govuk_organization.id'))
    govuk_organization = orm.relationship('GovukOrganization',
                                          backref='collections')
    published = Column(types.DateTime)
    last_updated = Column(types.DateTime)
    created = Column(types.DateTime, default=datetime.datetime.now)
    publications = orm.relationship('Publication',
                                    secondary=collection_publication_table,
                                    backref='collections')


class Publication(Base, SimpleDomainObject):
    __tablename__ = 'publication'
    id = Column(types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    govuk_id = Column(types.Integer, index=True)
    name = Column(types.UnicodeText, index=True)
    url = Column(types.UnicodeText)
    category = Column(types.UnicodeText)
    title = Column(types.UnicodeText, nullable=False)
    summary = Column(types.UnicodeText)
    detail = Column(types.UnicodeText)
    govuk_organization_id = Column(types.UnicodeText,
                                   ForeignKey('govuk_organization.id'))
    govuk_organization = orm.relationship(
        'GovukOrganization',
        primaryjoin='Publication.c.govuk_organization_id==GovukOrganization.c.id',
        backref=orm.backref(
            'collections',
            primaryjoin='Publication.c.govuk_organization_id==GovukOrganization.c.id',
            secondaryjoin='Publication.c.extra_govuk_organization_id==GovukOrganization.c.id',
            )
        )
    extra_govuk_organization_id = Column(types.UnicodeText,
                                         ForeignKey('govuk_organization.id'))
    extra_govuk_organization = orm.relationship(
        'GovukOrganization',
        primaryjoin='Publication.c.govuk_organization_id==GovukOrganization.c.id',
        )
    published = Column(types.DateTime)
    last_updated = Column(types.DateTime)
    created = Column(types.DateTime, default=datetime.datetime.now)


# e.g. https://www.gov.uk/government/publications/new-school-proposals has
# sector-link Academies and free schools
class Publink(Base, SimpleDomainObject):
    __tablename__ = 'publink'
    id = Column(types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    type = Column(types.UnicodeText)
    title = Column(types.UnicodeText)
    created = Column(types.DateTime, default=datetime.datetime.now)
    publications = orm.relationship('Publication',
                                    secondary=publication_publink_table,
                                    backref='publinks')


class Attachment(Base, SimpleDomainObject):
    __tablename__ = 'attachment'
    id = Column(types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    govuk_id = Column(types.Integer, index=True)
    name = Column(types.UnicodeText, index=True)
    publication_id = Column('publication_id', types.UnicodeText,
                            ForeignKey('publication.id'))
    # TODO: put in a particular ordering
    publication = orm.relationship('Publication',
            backref=orm.backref('attachments'))
    url = Column(types.UnicodeText)
    category = Column(types.UnicodeText)
    title = Column(types.UnicodeText, nullable=False)
    summary = Column(types.UnicodeText)
    detail = Column(types.UnicodeText)
    published = Column(types.DateTime)
    last_updated = Column(types.DateTime)
    created = Column(types.DateTime, default=datetime.datetime.now)


#orm.mapper(GovukOrganization, govuk_organization_table)
#orm.mapper(Collection, collection_table, properties={
#    'govuk_organization': orm.relation(
#        GovukOrganization,
#        backref=orm.backref('collection_all',
#                            cascade='all, delete-orphan')),
#    'publication': orm.relation(
#        Publication,
#        secondary=collection_publication_table),
#    })
#orm.mapper(Publication, publication_table, properties={
#    'govuk_organization': orm.relation(
#        GovukOrganization,
#        primaryjoin=Publication.c.govuk_organization_id==GovukOrganization.c.id,
#        backref=orm.backref(
#            'publication_all',
#            primaryjoin=Publication.c.govuk_organization_id==GovukOrganization.c.id,
#            secondaryjoin=Publication.c.extra_govuk_organization_id==GovukOrganization.c.id,
#            cascade='all, delete-orphan')),
#    })
#orm.mapper(Attachment, attachment_table, properties={
#    'publication': orm.relation(
#        Publication,
#        backref=orm.backref('attachment_all',
#                            cascade='all, delete-orphan')),
#    })

def init_tables():
    metadata.create_all(model.meta.engine)

