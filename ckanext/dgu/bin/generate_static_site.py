'''

'''
import os
import json
import threading
from optparse import OptionParser
from pylons import config

import common
from running_stats import Stats

import webtest
from ckan.config.middleware import make_app


def clean_response(s):
    pos = s.find("<!")
    return s[pos:]


class GenerateStaticSite(threading.Thread):

    def __init__(self, options, publishers, datasets):
        config['ckan.legacy_templates'] = False
        self.app = make_app(config['global_conf'], **config)
        self.app = webtest.TestApp(self.app)
        self.options =  options
        #TODO: Set path or default
        self.root = '/tmp/static'
        self._ensure_folder(self.root)
        self.publishers = publishers
        self.datasets = datasets
        super(GenerateStaticSite, self).__init__()


    def run(self):
        from ckan import model

        self.stats_pages = Stats()

        if not self.publishers and not self.datasets:
            content = self._get_publisher_root_page()
            self._write_file("", "publisher", content)

            content = self._get_spending_root_page()
            self._write_file("data/openspending-report", "index", content)

            # Get all publishers for spending reports, even though some
            # don't have one.
            publishers = common.get_publishers(state='active')
            for publisher in publishers:
                print "Spending: ", publisher.name
                content = self._get_spending_page(publisher.name)
                self._write_file("data/openspending-report", "publisher-".format(publisher.name), content)

            return

        print "Fetching publishers"
        count = 0
        total = len(self.publishers)

        for publisher in self.publishers:
            print "{} - {}".format(count, publisher.name)
            response = self._get_publisher_page(publisher.name)
            self.stats_pages.add("Added publisher", publisher.name)
            self._write_file("publisher", publisher.name, response)
            count += 1

        print "-" * 60

        print "Fetching datasets"
        count = 0
        total = len(self.datasets)

        print "Processing {} datasets".format(total)
        for dataset in self.datasets:
            response = self._get_package_page(dataset.name)
            if not response:
                self.stats_pages.add("Failed", dataset.name)
                continue

            self._write_file("dataset", dataset.name, response)
            self.stats_pages.add("Added package", dataset.name)

            for resource in common.get_resources(dataset_name=dataset.name):
                response = self._get_resource_page(dataset.name, resource.id)
                self.stats_pages.add("Added resource", resource.id)
                self._write_file("dataset/{}/resource/".format(dataset.name), resource.id, response)

            count += 1
            if count % 10 == 0:
                print "++ Processed {}/{}".format(count, total),

        print "-" * 60

        print self.stats_pages.report()
        self.stats_pages.show_time_taken()


    def _write_file(self, subfolder, name, content):
        fname = os.path.join(self.root, subfolder, name + ".html")
        self._ensure_folder(fname)
        with open(fname, 'w') as f:
            f.write(content)
            f.flush()


    def _ensure_folder(self, path):
        d = os.path.dirname(path)
        if not os.path.exists(d):
            os.makedirs(d)

    def _get_page(self, url):
        try:
            response = self.app.get(
                url=url
            )
            return response.body
        except Exception, e:
            print "FAILED: ", url, e
        return ""

    def _get_resource_page(self, dataset_name, resource_id):
        return self._get_page("/dataset/{}/resource/{}".format(dataset_name, resource_id))

    def _get_publisher_page(self, name):
        return self._get_page("/publisher/{}".format(name))

    def _get_publisher_root_page(self):
        return self._get_page("/publisher")

    def _get_spending_root_page(self):
        return self._get_page("/data/openspending-report/index")

    def _get_spending_page(self, name):
        return self._get_page("/data/openspending-report/publisher-{}.html".format(name))

    def _get_package_page(self, name):
        return self._get_page("/dataset/{}".format(name))


usage = '''
    python %prog $CKAN_INI
'''

if __name__ == '__main__':
    parser = OptionParser(description=__doc__.strip(), usage=usage)
    parser.add_option('-t', '--target', dest='target')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Wrong number of arguments')
    config_ini = args[0]

    common.load_config(config_ini)
    common.register_translator()

    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in xrange(0, len(l), n):
            yield l[i:i+n]

    publishers = common.get_publishers(state='active')
    publisher_count = len(publishers)
    publisher_generator = chunks(publishers, publisher_count/4)

    datasets = common.get_datasets(state='active')
    dataset_count = len(datasets)
    dataset_generator = chunks(datasets, dataset_count/4)

    # Partition the publishers and datasets and pass them to the
    # GenerateStaticSite command so we can thread them ...
    threads = [
        #GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
        #GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
        #GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
        #GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
        GenerateStaticSite(options, [], []),
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()


