import logging
import datetime

from sqlalchemy import types, Table, Column, ForeignKey, orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.exc import ProgrammingError

from ckan import model

log = logging.getLogger(__name__)

__all__ = ['Collection', 'Publication', 'Attachment', 'init_tables']

# to clear out:
# psql ckan -c 'drop table collection, publication, govuk_organization, attachment, publink, collection_publication, organization_publication_table, publication_publink;'

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

# A Publication can be from many Organizations
# e.g. https://www.gov.uk/government/publications/nhs-trusts-and-foundation-trusts-in-special-measures-1-year-on
organization_publication_table = Table(
    'organization_publication', Base.metadata,
    Column('id', types.UnicodeText, primary_key=True,
           default=model.types.make_uuid),
    Column('govuk_organization_id', types.UnicodeText, ForeignKey('govuk_organization.id')),
    Column('publication_id', types.UnicodeText, ForeignKey('publication.id')),
    Column('created', types.DateTime, default=datetime.datetime.now),
    )

publication_publink_table = Table(
    'publication_publink', Base.metadata,
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
    govuk_id = Column(types.UnicodeText, index=True)
    name = Column(types.UnicodeText, index=True)
    url = Column(types.UnicodeText)
    title = Column(types.UnicodeText, nullable=False)
    description = Column(types.UnicodeText)
    publications = orm.relationship('Publication',
            secondary=organization_publication_table,
            backref='govuk_organizations')


class Collection(Base, SimpleDomainObject):
    __tablename__ = 'collection'
    id = Column(types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    govuk_id = Column(types.UnicodeText, index=True)
    name = Column(types.UnicodeText, index=True)
    url = Column(types.UnicodeText)
    title = Column(types.UnicodeText, nullable=False)
    summary = Column(types.UnicodeText)
    # some but not all collections have more text - ignore it.
    govuk_organization_id = Column(types.UnicodeText,
                                   ForeignKey('govuk_organization.id'))
    govuk_organization = orm.relationship('GovukOrganization',
                                          backref='collections')
    created = Column(types.DateTime, default=datetime.datetime.now)
    publications = orm.relationship('Publication',
                                    secondary=collection_publication_table,
                                    backref='collections')

    @classmethod
    def by_govuk_id(cls, govuk_id):
        return model.Session.query(cls) \
                    .filter_by(url=govuk_id) \
                    .first()

    def __unicode__(self):
        repr = u'<%s' % self.__class__.__name__
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            try:
                value = unicode(getattr(self, col.name))
            except Exception, inst:
                value = unicode(inst)
            # truncate the summary
            if col.name == 'summary' and len(value) > 30:
                value = value[:30] + '...'
            repr += u' %s=%s' % (col.name, value)
        repr += ' publications=%s' % len(self.publications)
        return repr + '>'

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Publication(Base, SimpleDomainObject):
    __tablename__ = 'publication'
    id = Column(types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    govuk_id = Column(types.UnicodeText, index=True)
    # name is like "publications/jobseekers-allowance-sanctions-independent-review"
    # because of clashes like:
    # https://www.gov.uk/government/publications/jobseekers-allowance-sanctions-independent-review
    # https://www.gov.uk/government/consultations/jobseekers-allowance-sanctions-independent-review
    name = Column(types.UnicodeText, index=True)
    url = Column(types.UnicodeText)
    type = Column(types.UnicodeText)
    title = Column(types.UnicodeText, nullable=False)
    summary = Column(types.UnicodeText)
    detail = Column(types.UnicodeText)
    # TODO policies and other things 'Part of'
    published = Column(types.DateTime)  # When first published on gov.uk
    last_updated = Column(types.DateTime)  # None until the 2nd revision
    created = Column(types.DateTime, default=datetime.datetime.now)  # in CKAN

    @classmethod
    def by_govuk_id(cls, govuk_id):
        return model.Session.query(cls) \
                    .filter_by(govuk_id=govuk_id) \
                    .first()

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
    govuk_id = Column(types.UnicodeText, index=True)
    publication_id = Column('publication_id', types.UnicodeText,
                            ForeignKey('publication.id'))
    publication = orm.relationship('Publication',
            backref=orm.backref(
                'attachments',
                cascade='all, delete-orphan',
                order_by='Attachment.position',
                collection_class=ordering_list('position')))
    position = Column(types.Integer)
    url = Column(types.UnicodeText)
    filename = Column(types.UnicodeText)
    format = Column(types.UnicodeText)
    title = Column(types.UnicodeText)
    created = Column(types.DateTime, default=datetime.datetime.now)

    @classmethod
    def by_govuk_id(cls, govuk_id):
        return model.Session.query(cls) \
                    .filter_by(govuk_id=govuk_id) \
                    .first()


class Link(Base, SimpleDomainObject):
    __tablename__ = 'link'
    id = Column('id', types.UnicodeText, primary_key=True,
                default=model.types.make_uuid)
    govuk_table = Column(types.UnicodeText, nullable=False)
    govuk_id = Column(types.UnicodeText, nullable=False)
    ckan_table = Column(types.UnicodeText, nullable=False)
    ckan_id = Column(types.UnicodeText, nullable=False)
    created = Column(types.DateTime, default=datetime.datetime.now)

    @property
    def govuk(self):
        govuk_class = {'collection': Collection,
                       'publication': Publication,
                       'attachment': Attachment}[self.govuk_table]
        govuk_obj = govuk_class.by_govuk_id(self.govuk_id)
        return govuk_obj

    @property
    def ckan(self):
        ckan_class = {'dataset': model.Package,
                      'resource': model.Resource}[self.ckan_table]
        ckan_obj = ckan_class.get(self.ckan_id)
        return ckan_obj

    def __unicode__(self):
        try:
            govuk = self.govuk
            ckan = self.ckan
            return '<Link %s %s>' % (
                govuk.url,
                ckan.name if isinstance(ckan, model.Package) else
                '%s/%s' % (ckan.resource_group.package.name, ckan.id))
        except ProgrammingError:
            model.Session.remove()
            return '<Link %s=%s %s=%s>' % (self.govuk_table, self.govuk_id,
                                        self.ckan_table, self.ckan_id)

def init_tables():
    Base.metadata.create_all(model.meta.engine)

def rebuild():
    # needed, since model.repo.rebuild_all doesn't touch these tables
    model.Session.remove()
    tables = reversed(Base.metadata.sorted_tables)
    for table in tables:
        model.Session.execute('delete from "%s"' % table.name)
    model.Session.commit()
