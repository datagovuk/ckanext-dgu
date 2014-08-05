from ckanext.dgu.bin.running_stats import Stats
from ckanext.dgu.model import govuk_publications as govuk_pubs_model
from ckan import model


class GovukPublicationLinks(object):
    @classmethod
    def autolink(cls, resource_id=None, dataset_name=None):
        stats = Stats()
        resources = get_resources(resource_id=resource_id, dataset_name=dataset_name)
        print '%i resources to gov.uk' % len(resources)
        for res in resources:
            pkg = res.resource_group.package
            pubs = model.Session.query(govuk_pubs_model.Publication) \
                        .filter_by(url=res.url) \
                        .all()
            attachments = model.Session.query(govuk_pubs_model.Attachment) \
                        .filter_by(url=res.url) \
                        .all()
            links = len(pubs) * ['publication'] + len(attachments) * ['attachment']
            print stats.add('%s links' % ', '.join(links), '%s.%s' % (pkg.name, res.position))
        print stats


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
