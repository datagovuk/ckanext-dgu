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
    def autoadd(cls, publication_url=None):
        cls.stats = Stats()
        if publication_url:
            try:
                publication = \
                    model.Session.query(govuk_pubs_model.Publication)\
                         .filter_by(url=publication_url).one()
                cls.add_or_update_publication(publication)
            except sqlalchemy.orm.exc.NoResultFound:
                cls.stats.add('Error looking up Publication', publication_url)
        else:
            publications = model.Session.query(govuk_pubs_model.Publication)
            for publication in publications:
                cls.add_or_update_publication(publication)
                #break

        print cls.stats

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
        the name of a dgu organisation, or None if not found.  Those
        not found will be added to stats to ensure we have a record.
        """
        remote_publisher = publication.govuk_organizations[0]
        publisher = GovukPublications.organization_map.get(remote_publisher.name)

        if not publisher:
            publisher = model.Group.get(remote_publisher.name)

        if not publisher:
            cls.stats.add("Unable to find organisation for",
                remote_publisher.name)
        else:
            GovukPublications.organization_map[remote_publisher.name] = publisher

        return publisher

    @classmethod
    def add_or_update_publication(cls, publication):
        query = model.Session.query(govuk_pubs_model.Link.ckan_id.distinct())\
                    .filter_by(govuk_id=publication.govuk_id)\
                    .filter_by(govuk_table='publication')\
                    .filter_by(ckan_table='dataset')
        try:
            ckan_id = query.one()[0]
            cls.stats.add('Updating Publication', publication.id)
            package = model.Package.get(ckan_id)
        except sqlalchemy.orm.exc.NoResultFound:
            cls.stats.add('Adding Publication', publication.id)
            package = None
        except sqlalchemy.orm.exc.MultipleResultsFound:
            # TODO: Work out if this is a mistake at scraping, or whether
            # it is expected sometimes.
            print "Found duplicate datasets for publication - skipping:"
            for link in query.all():
                print "", link[0]
                return

        publisher = cls.govuk_org_to_dgu_org(publication)
        print publisher
        if not publisher:
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
