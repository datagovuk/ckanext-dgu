import os
import sys
import datetime
import time
import logging
import threading
from multiprocessing import Process
from ckan.lib.cli import CkanCommand

log = logging.getLogger('ckanext')

class SolrStressTest(CkanCommand):
    """
    Performs batches of queries in an attempt to stress
    solr so that it shows bad behaviour (wrt heap)
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0


    def __init__(self, name):
        super(SolrStressTest, self).__init__(name)
        self.parser.add_option("-s","--server",
                  type="string", dest="server",
                  default="",
                  help="Specifies the server API to connect to")
        self.parser.add_option("-t","--times",
                  type="int", dest="times",
                  default="1",
                  help="How many time to run the test in each process")
        self.parser.add_option("-k","--count",
                  type="int", dest="count",
                  default="50",
                  help="How many items to pull from valid/invalid lists")

    def command(self):
        self._load_config()

        import ckan.model as model
        from ckan.logic import get_action

        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")

        site_user = get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})
        apikey = site_user['apikey']

        self.invalid_ids = ['id:%d' % x for x in xrange(1,10000)]
        self.valid_ids = ["id:%s" % p.id for p in model.Session.query(model.Package).filter(model.Package.state=='active').all()]

        s = time.time()
        procs = []
        args = (self.valid_ids, self.invalid_ids, apikey, self.options.server, self.options.times, self.options.count,)
        for x in range(10):
            p = Process(target=searcher, args=args)
            procs.append(p)
            p.start()
        for x in range(10):
            p.join()
        print time.time()-s


def searcher(valid_ids, invalid_ids, apikey, server, times=1, count=50):
    import time
    import random
    import ckanclient

    errors = []
    for _ in range(times):
        valid = random.randint(5, count)
        invalid = random.randint(5, count)

        samples = random.sample(valid_ids, valid)
        samples.extend(random.sample(invalid_ids, invalid))

        s = time.time()
        ckan = ckanclient.CkanClient(base_location=server, api_key=apikey)
        opts = {'offset': 0,
                'limit': 0}
        q = ' OR '.join(samples)

        try:
            search_results = ckan.package_search(q, opts)
            datasets = list(search_results['results'])
            log.info("%d items found from %d ids in %s" % (len(datasets),valid+invalid,time.time() - s))
        except:
            log.error("Search failed with %d valid and %d invalid items in query" % (valid,invalid,))

