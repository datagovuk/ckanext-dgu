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

        #root = self._get_publisher_root_page()
        #self._write_file("", "publisher", root)

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


    def _get_resource_page(self, dataset_name, resource_id):
        response = self.app.get(
            url="/dataset/{}/resource/{}".format(dataset_name, resource_id)
        )
        return response.body

    def _get_publisher_page(self, name):
        try:
            group_controller = 'ckanext.dgu.controllers.publisher:PublisherController'
            response = self.app.get(
                url="/publisher/{}".format(name)
            )
            return response.body
        except Exception, e:
            print "FAILED: ", name, e
        return ""

    def _get_publisher_root_page(self):
        try:
            response = self.app.get(
                url="/publisher",
            )
            return response.body
        except Exception, e:
            print "FAILED: ", name, e
            raise e
        return ""

    def _get_package_page(self, name):
        try:
            dgu_package_controller = 'ckanext.dgu.controllers.package:PackageController'
            response = self.app.get(
                url="/dataset/{}".format(name)
            )
            return response.body
        except Exception, e:
            print "FAILED: ", name, e
            raise e
        return ""


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
        GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
        GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
        GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
        GenerateStaticSite(options, publisher_generator.next(), dataset_generator.next()),
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()


