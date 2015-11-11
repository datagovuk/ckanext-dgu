import sqlalchemy

from ckanext.dgu.model import govuk_publications as govuk_pubs_model
from ckanext.dgu.bin.running_stats import Stats
from ckanext.harvest.harvesters.base import HarvesterBase
from ckan import model
import ckan.plugins as p


class GovukPublications(object):
    @classmethod
    def update(cls, publication_url=None):
        '''Updates existing datasets based on their links to publications'''
        if publication_url:
            return cls._add_or_update_publication_by_url(publication_url)

        cls.stats = Stats()
        publications_with_any_link_to_datasets = \
            model.Session.query(govuk_pubs_model.Publication)\
                 .join(govuk_pubs_model.Link,
                       govuk_pubs_model.Link.govuk_id ==
                       govuk_pubs_model.Publication.govuk_id)\
                 .filter_by(govuk_table='publication')\
                 .filter_by(ckan_table='dataset')\
                 .join(model.Package,
                       govuk_pubs_model.Link.ckan_id == model.Package.id)\
                 .distinct()\
                 .all()
        print 'Publications with links to datasets: %s' % \
            len(publications_with_any_link_to_datasets)
        for publication in publications_with_any_link_to_datasets:
            cls._add_or_update_publication(publication)

        print cls.stats

    @classmethod
    def add(cls, publication_url=None):
        '''Adds datasets for publications that have no existing links to
        datasets in our field
        '''
        if publication_url:
            return cls._add_or_update_publication_by_url(publication_url)

        cls.stats = Stats()
        links_to_datasets = \
            model.Session.query(govuk_pubs_model.Link.govuk_id)\
                 .filter_by(govuk_table='publication')\
                 .filter_by(ckan_table='dataset')
        publications_with_no_link_to_datasets =\
            model.Session.query(govuk_pubs_model.Publication)\
                 .filter(~govuk_pubs_model.Publication.govuk_id.in_(
                         links_to_datasets))\
                 .all()
        print 'Publications with no links to datasets: %s' % \
            len(publications_with_no_link_to_datasets)
        for publication in publications_with_no_link_to_datasets:
            cls._add_or_update_publication(publication)

        print cls.stats

    @classmethod
    def _add_or_update_publication_by_url(cls, publication_url):
        try:
            publication = \
                model.Session.query(govuk_pubs_model.Publication)\
                     .filter_by(url=publication_url).one()
            cls._add_or_update_publication(publication)
        except sqlalchemy.orm.exc.NoResultFound:
            print 'Error looking up Publication URL: %s' % publication_url

    @classmethod
    def _add_or_update_publication(cls, publication):
        try:
            link = model.Session.query(govuk_pubs_model.Link)\
                        .filter_by(govuk_id=publication.govuk_id)\
                        .filter_by(govuk_table='publication')\
                        .filter_by(ckan_table='dataset').one()
            cls.stats.add('Updating Publication', publication.id)
            package = link.ckan
        except sqlalchemy.orm.exc.NoResultFound:
            cls.stats.add('Adding Publication', publication.id)
            package = None

        context = {'model': model,
                   'session': model.Session,
                   'user': 'script'}

        pkg_dict = {
            'name': HarvesterBase._gen_new_name(publication.title),
            'title': publication.title,
            'notes': publication.summary,
            'license_id': 'uk-ogl',
            'owner_org': 'cabinet-office',
            'resources': [],
        }

        for attachment in publication.attachments:
            resource = {
                'url': attachment.url,
                'description': attachment.title,
            }
            pkg_dict['resources'].append(resource)

        if package:
            pkg_dict['id'] = package.id
            package = p.toolkit.get_action('package_update')(context, pkg_dict)
        else:
            package = p.toolkit.get_action('package_create')(context, pkg_dict)

            link = govuk_pubs_model.Link(govuk_id=publication.govuk_id,
                                         govuk_table='publication',
                                         ckan_table='dataset',
                                         ckan_id=package['id'])
            model.Session.add(link)
            model.Session.commit()
