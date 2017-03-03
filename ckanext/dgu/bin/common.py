import os

class ScriptError(Exception):
    pass


def get_ckanapi(config_ini_or_ckan_url, **kwargs):
    '''Given a config.ini filepath or a remote CKAN URL, returns a ckanapi
    instance that you can use to call action commands
    '''
    import ConfigParser
    print 'Connecting to CKAN...'
    import ckanapi
    import sys
    if config_ini_or_ckan_url.startswith('http'):
        # looks like a hostname e.g. https://data.gov.uk
        ckan_url = config_ini_or_ckan_url
        # Load the apikey from a config file
        config = ConfigParser.ConfigParser()
        config_filepath = '~/.ckan'
        try:
            config.read(os.path.expanduser(config_filepath))
            apikey = config.get(ckan_url, 'apikey')
        except ConfigParser.Error, e:
            print 'Error reading file with api keys configured: %s' % e
            print 'Ensure you have a file: %s' % config_filepath
            print 'With the api key of the ckan user "script", something like:'
            print '  [%s]' % ckan_url
            print '  apikey = fb3355-b55234-4549baac'
            sys.exit(1)
        ckan = ckanapi.RemoteCKAN(ckan_url,
                                  apikey=apikey,
                                  user_agent='dgu script',
                                  **kwargs)
    else:
        # must be a config.ini filepath
        load_config(config_ini_or_ckan_url)
        register_translator()
        # use 'script' username to identify bulk changes by script (rather than
        # a publisher)
        ckan = ckanapi.LocalCKAN(username='script')
    print '...connected.'
    return ckan


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

def get_config_value_without_loading_ckan_environment(config_filepath, key):
    '''May raise exception ValueError'''
    import ConfigParser
    config = ConfigParser.ConfigParser()
    try:
        config.read(os.path.expanduser(config_filepath))
        return config.get('app:main', key)
    except ConfigParser.Error, e:
        err = 'Error reading CKAN config file %s to get key %s: %s' % (
            config_filepath, key, e)
        raise ValueError(err)

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
    Returns resources, filtered by command-line options 'dataset' and
    'resource'.
    TODO: add filter by organization_ref
    '''
    return get_resources(state=state, resource_id=options.resource,
                         dataset_name=options.dataset)


def get_resources(state='active', resource_id=None, dataset_name=None):
    ''' Returns all active resources, or filtered by the given criteria.
    TODO: add filter by organization_ref
    '''
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

def get_datasets_using_options(options, state='active'):
    '''
    Returns (from the local db) datasets, filtered by command-line option 'dataset'.
    TODO: add filter by organization_ref
    '''
    return get_datasets(state=state, dataset_name=options.dataset)

def get_datasets(state='active', dataset_name=None, organization_ref=None):
    ''' Returns (from the local db) all active datasets, or filtered by the
    given criteria. '''
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


def get_datasets_via_api(ckan, options=None, q=None, fq=None,
                         dataset_name=None, organization_ref=None):
    ''' Returns (from a ckanapi object) all active datasets, or filtered by the
    given criteria. 'options' is common command-line options.'''
    q = q or '*:*'
    fq = fq or {}
    if options and hasattr(options, 'organization'):
        organization_ref = options.organization
    if options and hasattr(options, 'dataset'):
        dataset_name = options.dataset
    if organization_ref:
        if is_id(organization_ref):
            org_id = organization_ref
        else:
            from ckan import model
            org = model.Group.get(organization_ref)
            assert org
            org_id = org.id
        fq['owner_org'] = org_id
    if dataset_name:
        if isinstance(dataset_name, list):
            # use regex to search for multiple names
            # name:/(name1|name2)/
            dataset_name = '/(%s)/' % '|'.join(dataset_name)
        fq['name'] = dataset_name
    fq_str = ' '.join('%s:%s' % (k, v) for k, v in fq.items())
    page_size = 200
    search_options = dict(q=q, fq=fq_str, start=0, rows=page_size)
    print 'Package Search: ', search_options
    while True:
        response = ckan.action.package_search(**search_options)
        if not response['results']:
            break
        print 'Package progress: %s/%s' % \
            (search_options['start'], response['count'])
        for result in response['results']:
            yield result
        search_options['start'] += page_size


def name_stripped_of_url(url_or_name):
    '''Returns a name. If it is in a URL it strips that bit off.

    e.g. https://data.gov.uk/publisher/barnet-primary-care-trust
         -> barnet-primary-care-trust

         barnet-primary-care-trust
         -> barnet-primary-care-trust
    '''
    if url_or_name.startswith('http'):
        return url_or_name.split('/')[-1]
    return url_or_name


def is_id(id_string):
    '''Returns whether the string looks like a revision id or not'''
    import re
    reg_ex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(reg_ex, id_string))

def add_progress_bar(iterable, maxval=None, caption=None):
    '''Add a progress bar, to the thing you are doing a "for" loop over, if
    "progressbar" is installed.

    Note: if you see this:
              File "/home/co/ckan/local/lib/python2.7/site-packages/progressbar/__init__.py", line 208, in percentage
                return self.currval * 100.0 / self.maxval
            TypeError: unsupported operand type(s) for /: 'float' and 'classobj'
        then you need to specify the maxval parameter.
    '''
    try:
        import progressbar
        bar = progressbar.ProgressBar(widgets=[
            (caption + ' ') if caption else '',
            progressbar.Percentage(), ' ',
            progressbar.Bar(), ' ', progressbar.ETA()],
            maxval=maxval)
        return bar(iterable)
    except ImportError:
        return iterable

def parse_jsonl(filepath):
    '''Opens a JSONL file and yields each line as python dict/list'''
    with gzip.open(filepath, 'rb') as f:
        while True:
            line = f.readline()
            if line == '':
                break
            line = line.rstrip('\n')
            if not line:
                continue
            try:
                yield json.loads(line,
                                 encoding='utf8')
            except Exception:
                traceback.print_exc()
                import pdb
                pdb.set_trace()