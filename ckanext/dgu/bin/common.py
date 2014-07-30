import os

class ScriptError(Exception):
    pass

def remove_readonly_fields(pkg):
    '''Takes a package dictionary and gets rid of any read-only fields
    so that you can write the package to the API.'''
    for read_only_field in ('id', 'relationships', 'ratings_average',
                            'ratings_count', 'ckan_url',
                            'metadata_modified',
                            'metadata_created'):
        if pkg.has_key(read_only_field):
            del pkg[read_only_field]

def load_config(config_filepath):
    import paste.deploy
    config_abs_path = os.path.abspath(config_filepath)
    conf = paste.deploy.appconfig('config:' + config_abs_path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def register_translator():
    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from paste.registry import Registry
    from pylons import translator
    from ckan.lib.cli import MockTranslator
    global registry
    registry=Registry()
    registry.prepare()
    global translator_obj
    translator_obj=MockTranslator()
    registry.register(translator, translator_obj)


def get_resources_using_options(options, state='active'):
    '''
    Returns resources, filtered by commandline options 'dataset' and
    'resource'.
    '''
    return get_resources(state=state, resource_id=options.resource,
                         dataset_name=options.dataset)


def get_resources(state='active', resource_id=None, dataset_name=None):
    ''' Returns all active resources, or filtered by the given criteria. '''
    from ckan import model
    resources = model.Session.query(model.Resource) \
                .filter_by(state=state) \
                .join(model.ResourceGroup) \
                .join(model.Package) \
                .filter_by(state='active')
    criteria = [state]
    if resource_id:
        resources = resources.filter(model.Resource.id==resource_id)
        criteria.append('Resource:%s' % resource_id)
    elif dataset_name:
        resources = resources.filter(model.Package.name==dataset_name)\
                             .order_by(model.Resource.position)
        criteria.append('Dataset:%s' % dataset_name)
    else:
        resources = resources.order_by(model.Package.name)
    resources = resources.all()
    print '%i resources (%s)' % (len(resources), ' '.join(criteria))
    return resources

def get_datasets(state='active', dataset_name=None, organization_ref=None):
    ''' Returns all active datasets, or filtered by the given criteria. '''
    from ckan import model
    datasets = model.Session.query(model.Package) \
                    .filter_by(state=state)
    criteria = [state]
    if dataset_name:
        datasets = datasets.filter_by(name=dataset_name)
        criteria.append('Dataset:%s' % dataset_name)
    if organization_ref:
        org = model.Group.get(organization_ref)
        assert org
        datasets = datasets.filter_by(owner_org=org.id)
        criteria.append('Organization:%s' % org.name)
    datasets = datasets.all()
    print '%i datasets (%s)' % (len(datasets), ' '.join(criteria))
    return datasets

