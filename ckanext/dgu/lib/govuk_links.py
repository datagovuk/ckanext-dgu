from collections import defaultdict

from sqlalchemy.orm.exc import DetachedInstanceError

from ckanext.dgu.bin.running_stats import Stats
from ckanext.dgu.model import govuk_publications as govuk_pubs_model
from ckan import model


class GovukPublicationLinks(object):
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
