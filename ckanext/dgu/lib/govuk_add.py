import sqlalchemy

from ckanext.dgu.model import govuk_publications as govuk_pubs_model
import ckanext.dgu.lib.theme
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
    def update(cls, publication_url=None):
        '''Updates existing datasets based on their links to publications'''
        cls.stats = Stats()

        if publication_url:
            ret = cls._add_or_update_publication_by_url(publication_url)
            print cls.stats
            return ret

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
            print 'Updating Publication', publication.name
            cls._add_publication(publication)

        print cls.stats

    @classmethod
    def add(cls, publication_url=None):
        '''Adds datasets for publications that have no existing links to
        datasets in our field
        '''
        cls.stats = Stats()

        if publication_url:
            ret = cls._add_or_update_publication_by_url(publication_url)
            print cls.stats
            return ret

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
            print 'Adding Publication', publication.name
            cls._add_publication(publication)

        print cls.stats

    @classmethod
    def _normalise_format(cls, format):
        formats = {
            "Plain text": "TXT",
            "MS Powerpoint Presentation": "PPT",
            "MS Excel Spreadsheet": "XLS",
            "MS Word Document": "DOC"
        }
        return formats.get(format, format)

    @classmethod
    def _govuk_org_to_dgu_org(cls, govuk_org_name, govuk_org_title):
        publisher = GovukPublications.organization_map.get(govuk_org_name)
        if not publisher:
            publisher = model.Group.get(govuk_org_name)
            if not publisher:
                publisher = model.Session.query(model.Group) \
                    .filter_by(title=govuk_org_title) \
                    .first()

        if not publisher:
            cls.stats.add('Error - unable to find organisation for',
                          govuk_org_name)
        else:
            GovukPublications.organization_map[govuk_org_name] = publisher

        return publisher

    @classmethod
    def _add_or_update_publication_by_url(cls, publication_url):
        # look up the publication
        try:
            publication = \
                model.Session.query(govuk_pubs_model.Publication)\
                     .filter_by(url=publication_url).one()
        except sqlalchemy.orm.exc.NoResultFound:
            print cls.stats.add('Error - looking up Publication URL',
                                publication_url)
            return
        cls._add_or_update_publication(publication)

    @classmethod
    def _add_or_update_publication(cls, publication):
        # see if there is an existing link to a dataset
        datasets = \
            model.Session.query(model.Package)\
            .join(govuk_pubs_model.Link,
                  model.Package.id == govuk_pubs_model.Link.ckan_id)\
            .filter_by(govuk_id=publication.govuk_id)\
            .filter_by(govuk_table='publication')\
            .filter_by(ckan_table='dataset')\
            .all()
        if len(datasets) == 1:
            cls._update_dataset(datasets[0])
        elif not datasets:
            cls._add_publication(publication)
        else:
            # multiple links
            print cls.stats.add('Error - multiple links to datasets',
                                '%s %s' %
                                (publication.govuk_url, len(datasets)))
            for dataset in datasets:
                print dataset

    @classmethod
    def _update_dataset(cls, dataset):
        # TODO
        publications = \
            model.Session.query(govuk_pubs_model.Publication)\
            .join(govuk_pubs_model.Link,
                  govuk_pubs_model.Publication.govuk_id ==
                  govuk_pubs_model.Link.govuk_id)\
            .filter_by(govuk_table='publication')\
            .filter_by(ckan_id=dataset.id)\
            .filter_by(ckan_table='dataset')\
            .all()

        dataset_dict = cls._get_dataset_dict(dataset.name, publications)
        if not dataset_dict:
            print cls.stats.add('Error getting dataset_dict', dataset.name)
            return
        dataset_dict['id'] = dataset.id

        context = {'model': model,
                   'session': model.Session,
                   'user': 'script'}
        dataset = p.toolkit.get_action('package_update')(context, dataset_dict)
        print cls.stats.add('Updated Dataset', dataset['name'])

    @classmethod
    def _add_publication(cls, publication):
        dataset_dict = cls._get_dataset_dict(dataset_name=None,
                                             publications=[publication])
        if not dataset_dict:
            print cls.stats.add('Error getting dataset_dict', publication.name)
            return

        context = {'model': model,
                   'session': model.Session,
                   'user': 'script'}
        dataset = p.toolkit.get_action('package_create')(context, dataset_dict)

        link = govuk_pubs_model.Link(govuk_id=publication.govuk_id,
                                     govuk_table='publication',
                                     ckan_table='dataset',
                                     ckan_id=dataset['id'])
        model.Session.add(link)
        model.Session.commit()
        print cls.stats.add('Added Publication',
                            '%s %s' % (publication.name, dataset.name))

    @classmethod
    def _get_property_across_govuk_publications(cls, publications, key):
        values = []
        for publication in publications:
            val = getattr(publication, key)
            if isinstance(val, list):
                values.extend(val)
            elif val:
                values.append(val)
        return values

    @classmethod
    def _get_first_non_none(cls, values):
        for value in values:
            if value:
                return value

    @classmethod
    def _get_dataset_dict(cls, dataset_name, publications):
        '''Returns a dataset_dict for the given publications, comprising the
        given govuk objects.

        # TODO add attachments and collections to the parameters
        '''
        # map govuk organization
        govuk_orgs = cls._get_property_across_govuk_publications(
            publications, 'govuk_organizations')
        if len(set(govuk_orgs)) > 1:
            print 'Warning: multiple gov.uk organizations for dataset %s: %s' \
                % (dataset_name, govuk_orgs)
        dgu_orgs = [cls._govuk_org_to_dgu_org(govuk_org.name, govuk_org.title)
                    for govuk_org in govuk_orgs]
        dgu_org = cls._get_first_non_none(dgu_orgs)
        if not dgu_org:
            print 'Could not map any publisher for dataset: %s from: %s' \
                % (dataset_name, [o.title for o in govuk_orgs])
            return
        print 'DGU org: %s', dgu_org.name

        # title
        titles = cls._get_property_across_govuk_publications(
            publications, 'title')
        if len(set(titles)) > 1:
            print 'Warning: multiple titles for dataset %s: %s' \
                % (dataset_name, titles)
        title = cls._get_first_non_none(titles)

        # title
        summaries = cls._get_property_across_govuk_publications(
            publications, 'summary')
        if len(set(summaries)) > 1:
            print 'Warning: multiple summary values for dataset %s: %s' \
                % (dataset_name, summaries)
        summary = cls._get_first_non_none(summaries)

        name = HarvesterBase._gen_new_name(title, existing_name=dataset_name)

        dataset_dict = {
            'name': name,
            'title': title,
            'notes': summary,
            'license_id': 'uk-ogl',
            'owner_org': dgu_org.id,
            'resources': [],
            'tags': [],
            'extras': [],
        }

        # resources
        for publication in publications:
            for attachment in publication.attachments:
                resource = {
                    'url': attachment.url,
                    'description': attachment.title,
                    'format': cls._normalise_format(attachment.format),
                }
                dataset_dict['resources'].append(resource)

        # theme
        ckanext.dgu.lib.theme.log.enabled = False
        themes = categorize_package(dataset_dict)
        if themes:
            dataset_dict['extras'].append({'key': PRIMARY_THEME,
                                           'value': themes[0]})
            dataset_dict['extras'].append({'key': SECONDARY_THEMES,
                                           'value': themes[1:]})

        return dataset_dict
