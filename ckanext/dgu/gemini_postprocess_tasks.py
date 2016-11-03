import os

from ckan.lib.celery_app import celery
import ckan.plugins as p

from ckanext.dgu.gemini_postprocess import process_package_


def create_package_task(package, queue):
    from pylons import config
    from ckan.model.types import make_uuid
    log = __import__('logging').getLogger(__name__)
    task_id = '%s/%s' % (package.name, make_uuid()[:4])
    ckan_ini_filepath = os.path.abspath(config['__file__'])
    celery.send_task('gemini_postprocess.process_package',
                     args=[ckan_ini_filepath, package.id, queue],
                     task_id=task_id, queue=queue)
    log.debug('Gemini PostProcess of package put into celery queue %s: %s',
              queue, package.name)


@celery.task(name="gemini_postprocess.process_package")
def process_package(ckan_ini_filepath, package_id, queue='bulk'):
    '''
    Archive a package.
    '''
    load_config(ckan_ini_filepath)
    register_translator()

    log = process_package.get_logger()
    log.info('Starting gemini process_package task: package_id=%r queue=%s', package_id, queue)

    # Do all work in a sub-routine since it can then be tested without celery.
    # Also put try/except around it is easier to monitor ckan's log rather than
    # celery's task status.
    try:
        process_package_(package_id)
    except Exception, e:
        if os.environ.get('DEBUG'):
            raise
        # Any problem at all is logged and reraised so that celery can log it too
        log.error('Error occurred during gemini post-process of package: %s\nPackage: %r %r',
                  e, package_id, package['name'] if 'package' in dir() else '')
        raise


def load_config(ckan_ini_filepath):
    import paste.deploy
    config_abs_path = os.path.abspath(ckan_ini_filepath)
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
    registry = Registry()
    registry.prepare()
    global translator_obj
    translator_obj = MockTranslator()
    registry.register(translator, translator_obj)


def _update_search_index(package_id, log):
    '''
    Tells CKAN to update its search index for a given package.
    '''
    from ckan import model
    from ckan.lib.search.index import PackageSearchIndex
    package_index = PackageSearchIndex()
    context_ = {'model': model, 'ignore_auth': True, 'session': model.Session,
                'use_cache': False, 'validate': False}
    package = p.toolkit.get_action('package_show')(
        context_, {'id': package_id})
    package_index.index_package(package, defer_commit=False)
    log.info('Search indexed %s', package['name'])
