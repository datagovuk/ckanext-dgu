from collections import defaultdict

from sqlalchemy.orm.exc import DetachedInstanceError

from ckanext.dgu.bin.running_stats import Stats
from ckanext.dgu.model import govuk_publications as govuk_pubs_model
import ckan.logic as logic
from ckan import model


class GovukPublicationLinks(object):

    @classmethod
    def fix_local_resources(cls, resource_id=None, dataset_name=None):
        """
        Find local resources that point to publications instead of attachments
        and fix them to either:
            1. Delete the resource if we have the a Publication that is linked to a Dataset
            2. If the resource points at a Publication that does not have a Dataset - chances are
                that resource.resource_group.package is the dataset - create the link
            3. We do not have a Publication that shares a URL with this resource - call function
                to create it.
        """
        stats = Stats()
        results = get_packages_and_resources(resource_id=resource_id,
                                                                        dataset_name=dataset_name,
                                                                        url_like="https://www.gov.uk/government/publications/%")

        resource_deletion = defaultdict(list)

        res_count = 0
        for _, v in results.iteritems():
            res_count += len(v)
        print '%i broken packages with %i broken resources that point to a publication page on GOV.UK' % (len(results), res_count,)

        for pkg_id, resource_ids in results.iteritems():
            pkg = model.Package.get(pkg_id)

            for resource_id in resource_ids:
                # Is there a publication with the same URL?
                publication_link = publication_link_from_resource(resource_id)

                if publication_link:
                    # This resource points at a publication
                    publication_dataset_link = publication_link_to_dataset(pkg.id, publication_link.govuk_id)

                    if publication_dataset_link:
                        # The publication link for the resource points to a valid dataset
                        stats.add("Has a link to a publication which references a dataset", resource_id)

                        if publication_dataset_link.ckan_id != pkg.id:
                            # The dataset the publication references isn't the same one that the resource is in.
                            # Leave the scraper to import it into the right place.
                            stats.add("Resource references publication, but resource is in wrong dataset", resource_id)
                            resource_deletion[pkg.name].append(resource_id)

                    else:
                        # The publication link for the resource does not point at a dataset
                        stats.add("Has a link to a publication which DOES NOT reference a dataset", resource_id)
                        # TODO: Try resource.resource_group.package as the link ?
                        # TODO: Delete the resource

                else:
                        # This resource does not point at a publication, forward that URL for scraping.
                        # Either:
                        #   1. The publication isn't listed in a place where we can scrape
                        #   2. It no longer exists.
                        stats.add("Does not have a link to a publication", resource_id)

                        # We should probably delete this resource.
                        resource_deletion[pkg.name].append(resource_id)


        # For each entry in resource_deletion, we will call package_show and then modify the dict
        # before calling package_update.
        context = {'model': model, 'session': model.Session}
        for k, v in resource_deletion.iteritems():
            print "Checking in {p} for resources to delete".format(p=k)
            pkg_dict = logic.get_action('package_show')(context, {'id': k})
            print "Was", len(pkg_dict['resources'])

            new_resources = []
            for res_dict in pkg_dict.get('resources'):
                if res_dict['id'] not in v:
                    print "Deleting resource ", res_dict['id']
                    new_resources.append(res_dict)
            pkg_dict['resources'] = new_resources

            print len(pkg_dict['resources'])
            break
        print stats

    @classmethod
    def autolink(cls, resource_id=None, dataset_name=None):
        '''autolink - Find clear links between gov.uk and DGU'''
        stats = Stats()
        resources = get_resources(resource_id=resource_id, dataset_name=dataset_name)
        for res in resources:
            try:
                pkg = res.resource_group.package
            except DetachedInstanceError:
                # looks like we've just committed, so re-get the resource
                res = model.Resource.get(res.id)
                pkg = res.resource_group.package

            res_identity = '%s.%s' % (pkg.name, res.position)

            # Find the links
            objs_to_link = cls.find_govuk_objs_to_autolink(res.url)

            # Update the Link objects
            existing_links = model.Session.query(govuk_pubs_model.Link) \
                                  .filter_by(ckan_table='resource') \
                                  .filter_by(ckan_id=res.id) \
                                  .all()
            existing_link_ids = [link.govuk_id for link in existing_links]
            outcomes = defaultdict(list)
            needs_commit = False
            for govuk_type, obj in objs_to_link:
                if obj.govuk_id in existing_link_ids:
                    outcomes[govuk_type].append('unchanged')
                    existing_link_ids.remove(obj.govuk_id)
                else:
                    link = govuk_pubs_model.Link(
                            govuk_table=govuk_type.__tablename__,
                            govuk_id=obj.govuk_id,
                            ckan_table='resource',
                            ckan_id=res.id)
                    model.Session.add(link)
                    needs_commit = True
                    print 'LINK', link
                    outcomes[govuk_type].append('added')
            if existing_link_ids:
                for link in existing_links:
                    if link.govuk_id in existing_link_ids:
                        model.Session.delete(link)
                outcomes[govuk_type].append('removed')
                needs_commit = True
            if outcomes:
                outcomes_strs = ['%s %s' % (govuk_type.__name__,
                                            '/'.join(outcomes[govuk_type]))
                                 for govuk_type in outcomes.keys()]
                stats.add('Link %s' % ', '.join(outcomes_strs), res_identity)
            else:
                stats.add('No links', res_identity)

            if needs_commit:
                model.Session.commit()
                model.Session.remove()
        print stats

    @classmethod
    def find_govuk_objs_to_autolink(cls, res_url):
        objs_to_link = []
        for govuk_type in (govuk_pubs_model.Publication,
                           govuk_pubs_model.Attachment):
            objs_to_link_ = model.Session.query(govuk_type) \
                                 .filter_by(url=res_url) \
                                 .all()
            if objs_to_link_:
                objs_to_link.extend([(govuk_type, obj) for obj in objs_to_link_])
        return objs_to_link


def publication_link_to_dataset(pkg_id, pub_id):
    return  model.Session.query(govuk_pubs_model.Link)\
            .filter(govuk_pubs_model.Link.ckan_id == pkg_id )\
            .filter(govuk_pubs_model.Link.ckan_table == "package")\
            .filter(govuk_pubs_model.Link.govuk_table == "publication")\
            .filter(govuk_pubs_model.Link.govuk_id == pub_id).first()


def publication_link_from_resource(resource_id):
    return model.Session.query(govuk_pubs_model.Link)\
                        .filter(govuk_pubs_model.Link.ckan_id == resource_id )\
                        .filter(govuk_pubs_model.Link.ckan_table == "resource")\
                        .filter(govuk_pubs_model.Link.govuk_table == "publication").first()

def get_packages_and_resources(resource_id=None, dataset_name=None, url_like='https:\/\/www.gov.uk\/%'):
    ''' Returns all gov.uk resource ids grouped by the package_ids.'''
    from ckan import model
    resources = model.Session.query(model.Resource.id, model.Package.id) \
                .filter_by(state='active') \
                .filter(model.Resource.url.like(url_like)) \
                .join(model.ResourceGroup) \
                .join(model.Package) \
                .filter_by(state='active')
    criteria = ['gov.uk']
    if dataset_name:
        resources = resources.filter(model.Package.name==dataset_name)
        criteria.append('Dataset:%s' % dataset_name)
    if resource_id:
        resources = resources.filter(model.Resource.id==resource_id)
        criteria.append('Resource:%s' % resource_id)

    results = defaultdict(list)
    for r, p in resources.all():
        results[p].append(r)

    return results

def get_resources(resource_id=None, dataset_name=None):
    ''' Returns all gov.uk resources, or filtered by the given criteria. '''
    from ckan import model
    resources = model.Session.query(model.Resource) \
                .filter_by(state='active') \
                .filter(model.Resource.url.like('https:\/\/www.gov.uk\/%')) \
                .join(model.ResourceGroup) \
                .join(model.Package) \
                .filter_by(state='active')
    criteria = ['gov.uk']
    if dataset_name:
        resources = resources.filter(model.Package.name==dataset_name)
        criteria.append('Dataset:%s' % dataset_name)
    if resource_id:
        resources = resources.filter(model.Resource.id==resource_id)
        criteria.append('Resource:%s' % resource_id)
    resources = resources.all()
    print '%i resources (%s)' % (len(resources), ' '.join(criteria))
    return resources