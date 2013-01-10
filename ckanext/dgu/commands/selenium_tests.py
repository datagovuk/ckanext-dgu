
import os
import sys
import urllib2
import requests
import subprocess
import inspect
import time
import collections
import ConfigParser

from optparse import OptionParser
from selenium import selenium
from ckan.lib.cli import CkanCommand

log = __import__('logging').getLogger("ckanext")

class TestRunner(CkanCommand):
    """
    Runs selenium tests

    Prepares selenium for running tests by starting up
    the selemiun server (if necessary) and running all
    of the tests in the tests folder.

    Available commands are:
        install - fetches the selenium jar and installs it locally
        run - runs all of the tests, starting selenium as necessary
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def __init__(self, name):
        super(TestRunner, self).__init__(name)
        self.parser.add_option("-s", "--selenium",
                  type="string", dest="selenium_url",
                  help="Specify the selenium url")
        self.parser.add_option("-t", "--target",
                  type="string", dest="target_url",
                  help="Specify the server url")
        self.parser.add_option("--configfile",
                  type="string", dest="config_file",
                  help="Specifies the configuration file")


        self.selenium_process = None



    def command(self):
        log.info("Created TestRunner")
        self._load_config()

        import ckan.model as model
        model.Session.remove()
        model.Session.configure(bind=model.meta.engine)
        model.repo.new_revision()
        log.info("Database access initialised")


        cmd = self.args[0]
        if cmd not in ['install', 'run']:
            log.error("Unknown command [%s]" % cmd)
            sys.exit(1)

        root = os.path.abspath(os.path.join(__file__,
            "../../../../"))

        self.selenium_home = os.path.join(root, 'selenium')
        if not os.path.exists(self.selenium_home):
            log.info("Creating selenium home directory")
            os.makedirs(self.selenium_home)

        self.config = ConfigParser.ConfigParser()
        self.config.readfp(open(self.options.config_file or "selenium_test.ini"))

        getattr(self, '%s_task' % cmd)()

    def install_task(self):
        """ Installs selenium jar file """
        log.info("Running install task")
        url = "http://selenium.googlecode.com/files/selenium-server-standalone-2.28.0.jar"

        log.info("Downloading selenium")
        self._download(url, os.path.join(self.selenium_home,
            "selenium-server-standalone-2.28.0.jar"))

    def run_task(self):
        import urlparse

        selenium_url = self.options.selenium_url or self._run_selenium()
        target_url = self.options.target_url or "http://localhost:5000/data"
        obj = urlparse.urlparse(selenium_url)


        self.selenium = selenium(obj.hostname, obj.port, "*firefox", target_url)
        self.selenium.start()

        error_dict = collections.defaultdict(list)
        class_count, method_count = (0, 0,)

        base_cfg = dict([(k,v,) for k,v in self.config.items("*")])

        import ckanext.dgu.testtools.selenium_tests
        for name,cls in inspect.getmembers(sys.modules["ckanext.dgu.testtools.selenium_tests"], inspect.isclass):
            class_count += 1

            methods = [nm for (nm,_) in
                inspect.getmembers(cls, predicate=inspect.ismethod) if nm.startswith('test_')]
            if not methods:
                continue

            # Get config for test name by copying the base config and applying
            # the test specific config over the top.
            cfg = base_cfg.copy()
            if self.config.has_section(name):
                cfg.update(dict([(k,v,) for k,v in self.config.items(name)]))

            # Build an instance of the test class and call each test method
            instance = cls(self.selenium, cfg, log)
            log.info("Running tests in %s" % name)

            for method_name in methods:
                try:
                    method_count += 1
                    log.info(" Test: %s" % method_name)
                    getattr(instance, method_name)()
                except Exception as e:
                    error_dict["%s.%s" % (name, method_name)].append(e)
                    log.error(e)
                except AssertionError as b:
                    error_dict["%s.%s" % (name, method_name)].append(b)
                    log.error(b)


        # Cleanup
        self.selenium.stop()
        if self.selenium_process:
            log.info("Closing down our local selenium server")
            self.selenium_process.kill()

        log.info("Ran %d tests in %d classes" % (method_count, class_count,))

        for k,v in error_dict.iteritems():
            print k
            print '*' * 30
            for i in v:
                print i


    def _run_selenium(self):
        """ Check if selenium is already running locally, can we get any sort of response
            from http://127.0.0.1:4444/ """
        running = True
        try:
            r = requests.get('http://127.0.0.1:4444/')
        except:
            running = False

        log.info("A local selenium is running? %s" % running)
        if not running:
            log.info("Creating our own local selenium instance")
            args = ['java', '-jar', os.path.join(self.selenium_home, "selenium-server-standalone-2.28.0.jar")]
            self.selenium_process = subprocess.Popen(args)

            # We should pause to give it a second or two to startup
            time.sleep(10)
        return 'http://127.0.0.1:4444/'


    def _download(self, url, target):
        log.info("Downloading selenium to %s" % target)
        u = urllib2.urlopen(url)
        with open(target, 'wb') as f:
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])

            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                f.write(buffer)
                status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                status = status + chr(8)*(len(status)+1)
                print status,

