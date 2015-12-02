import itertools

import sqlalchemy

from ckanext.dgu.model import govuk_publications as govuk_pubs_model
from ckanext.dgu.lib.theme import (categorize_package,
                                   PRIMARY_THEME,
                                   SECONDARY_THEMES)
from ckanext.dgu.bin.running_stats import Stats
from ckanext.harvest.harvesters.base import HarvesterBase
from ckan import model
import ckan.plugins as p


class GovukPublications(object):

    organization_map = {}

    @classmethod
    def update(cls, publication_url=None, dataset_name=None):
        '''Updates existing datasets based on their links to publications'''
        if publication_url:
            return cls._add_or_update_publication_by_url(publication_url)
        if dataset_name:
            return cls._update_publication_by_dataset_name(dataset_name)

        cls.stats = Stats()
        cls.org_stats = Stats()
        # find the publications that have links to datasets
        # and return them grouped by dataset
        publications_by_dataset = \
            model.Session.query(govuk_pubs_model.Publication,
                                model.Package)\
                 .join(govuk_pubs_model.Link,
                       govuk_pubs_model.Link.govuk_id ==
                       govuk_pubs_model.Publication.govuk_id)\
                 .filter_by(govuk_table='publication')\
                 .filter_by(ckan_table='dataset')\
                 .join(model.Package,
                       govuk_pubs_model.Link.ckan_id == model.Package.id)\
                 .group_by(model.Package)\
                 .all()
        import pdb; pdb.set_trace()
        print 'Publications with links to datasets: %s' % \
            len(publications_with_any_link_to_datasets)
        for publication, dataset in publications_with_any_link_to_datasets:
            cls._add_or_update_publication(publication, dataset, mode='update')

        print 'Datasets:\n\n', cls.stats
        print 'Organizations:\n\n', cls.org_stats

    @classmethod
    def add(cls, publication_url=None):
        '''Adds datasets for publications that have no existing links to
        datasets in our field
        '''
        if publication_url:
            return cls._add_or_update_publication_by_url(publication_url)

        cls.stats = Stats()
        cls.org_stats = Stats()    
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
            cls._add_or_update_publication(publication, mode='add')

        print 'Publications:\n\n', cls.stats
        print 'Organizations:\n\n', cls.org_stats

    @classmethod
    def normalise_format(cls, format):
        formats = {
            "Plain text": "TXT",
            "MS Powerpoint Presentation": "PPT",
            "MS Excel Spreadsheet": "XLS",
            "MS Word Document": "DOC"
        }
        return formats.get(format, format)

    @classmethod
    def govuk_org_to_dgu_org(cls, publication):
        """ Given a govuk_organisation this method will return
        the name of a dgu organisation, or None if not found.
        """
        remote_publisher = publication.govuk_organizations[0]
        publisher = GovukPublications.organization_map.get(remote_publisher.name)

        if not publisher:
            publisher = model.Group.get(remote_publisher.name)

        if not publisher:
            cls.org_stats('No mapping for "%s"' %
                          remote_publisher.name.encode('ascii', 'ignore'), '')
        else:
            cls.org_stats('Mapped "%s"' %
                          remote_publisher.name.encode('ascii', 'ignore'), '')
            GovukPublications.organization_map[remote_publisher.name] = publisher

        return publisher

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
    def _update_publication_by_dataset_name(cls, dataset_name):
        dataset_and_publications = \
            model.Session.query(model.Package, govuk_pubs_model.Publication)\
                 .filter_by(name=dataset_name)\
                 .join(govuk_pubs_model.Link,
                       govuk_pubs_model.Link.ckan_id == model.Package.id)\
                 .filter_by(govuk_table='publication')\
                 .filter_by(ckan_table='dataset')\
                 .join(govuk_pubs_model.Publication,
                       govuk_pubs_model.Publication.govuk_id ==
                       govuk_pubs_model.Link.govuk_id)\
                 .order_by(model.Package.name)\
                 .all()
        import pdb; pdb.set_trace()
        if not dataset_and_publications:
            print 'Error looking up dataset name: %s' % dataset_name
            return
        publications = []
        dataset = dataset_and_publications[0][0]
        for dataset_, publication in dataset_and_publications:
            if dataset != dataset:
                print 'Multiple datasets match name: %s' % dataset_name
                return
            publications.append(publication)
        cls._add_or_update_publication(publications, dataset=dataset)

    @classmethod
    def _add_or_update_publication(cls, publication, dataset=None, mode=None):
        assert mode in ('add', 'update', None)

        # find the dataset to update
        if mode is None or (mode=='update' and dataset is None):
            datasets = \
                model.Session.query(govuk_pubs_model.Link.ckan_id, model.Package)\
                     .filter_by(govuk_id=publication.govuk_id)\
                     .filter_by(govuk_table='publication')\
                     .filter_by(ckan_table='dataset')\
                     .join(model.Package,
                           govuk_pubs_model.Link.ckan_id == model.Package.id)\
                     .group_by(model.Package)\
                     .all()
            if not datasets and mode is None:
                mode = 'update'
            elif not datasets:
                print cls.stats.add('Error - Could not update publication as '
                                    'dataset not found', publication.url)
                return
            elif len(datasets) > 1:
                # TODO: Work out if this is a mistake at scraping, or whether
                # it is expected sometimes.
                print cls.stats.add('Error - Found duplicate datasets for '
                                    'publication - skipping', publication.url)
                for dataset_id, dataset in datasets:
                    print "", link[0]
                    return
            else:
                dataset = datasets[0][1]

        publisher = cls.govuk_org_to_dgu_org(publication)
        print publisher
        if not publisher:
            cls.stats.add('Error - unable to map organisation - skipping',
                          publication.url)
            return

        context = {'model': model,
                   'session': model.Session,
                   'user': 'script'}

        pkg_dict = {
            'name': HarvesterBase._gen_new_name(publication.title),
            'title': publication.title,
            'notes': publication.summary,
            'license_id': 'uk-ogl',
            'owner_org': publisher.id,
            'resources': [],
            'tags': [],
            'extras': [],
        }

        for attachment in publication.attachments:
            resource = {
                'url': attachment.url,
                'description': attachment.title,
                'format': cls.normalise_format(attachment.format),
            }
            pkg_dict['resources'].append(resource)

        themes = categorize_package(pkg_dict)
        if themes:
            pkg_dict['extras'].append({'key': PRIMARY_THEME,
                                       'value': themes[0]})
            pkg_dict['extras'].append({'key': SECONDARY_THEMES,
                                       'value': themes[1:]})

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
