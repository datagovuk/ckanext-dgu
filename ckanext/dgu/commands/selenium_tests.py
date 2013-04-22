import os
import sys
import urllib2
import requests
import subprocess
import inspect
import time
import collections
import ConfigParser
import logging
import traceback

from optparse import OptionParser
from ckan.lib.cli import CkanCommand

log = None

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
        self.dgu_dir = os.path.abspath(os.path.join(__file__, "../../../../"))
        default_config_filepath = os.path.join(self.dgu_dir,
                                               'selenium_test.ini')
        self.parser.add_option("-s", "--selenium",
                  type="string", dest="selenium_url",
                  help="Specify the selenium url")
        self.parser.add_option("-t", "--target",
                  type="string", dest="target_url",
                  help="Specify the server url")
        self.parser.add_option("--configfile",
                  type="string", dest="config_file",
                               default=default_config_filepath,
                  help="Specifies the DGU Selenium configuration file")


        self.selenium_process = None



    def command(self):

        # Initialise logger after the config is loaded, so it is not disabled.
        global log
        log = logging.getLogger(__name__)
        log.info("Created TestRunner")

        cmd = self.args[0]
        if cmd not in ['install', 'run']:
            log.error("Unknown command [%s]" % cmd)
            sys.exit(1)

        self.selenium_home = os.path.join(self.dgu_dir, 'selenium')
        if not os.path.exists(self.selenium_home):
            log.info("Creating selenium home directory")
            os.makedirs(self.selenium_home)

        self.config = ConfigParser.ConfigParser()
        if self.options.config_file:
            config_filepath = self.options.config_file
        else:
            log.debug('No --configfile specified, so using default of: %s',
                      default_config_filepath)
            config_filepath = default_config_filepath

        if cmd == "run":
            # Currently only run uses config, and this will be generated for
            # us by a fab task in most cases.
            self.config.readfp(open(self.options.config_file or \
                                    default_config_filepath))

        getattr(self, '%s_task' % cmd)()

    def install_task(self):
        """ Installs selenium jar file """
        log.info("Running install task")
        url = "http://selenium.googlecode.com/files/selenium-server-standalone-2.28.0.jar"

        log.info("Downloading selenium")
        self._download(url, os.path.join(self.selenium_home,
            "selenium-server-standalone-2.28.0.jar"))

    def run_task(self):
        global log
        import urlparse
        from selenium import selenium, webdriver

        selenium_url = self.options.selenium_url or self._run_selenium()
        target_url = self.options.target_url or "http://localhost:5000/data"
        obj = urlparse.urlparse(selenium_url)

        print "Requesting selenium connect to: %s" % (target_url,)

        self.selenium = selenium(obj.hostname, obj.port, "*webdriver", target_url)
        driver = webdriver.Remote(command_executor="http://localhost:8910",
            desired_capabilities={'takeScreenshot':False,'javascriptEnabled':True,'webdriver.remote.sessionid':1})
        self.selenium.start(driver=driver)

        try:
            error_dict = collections.defaultdict(list) # {test_name: [message, ..]}
            class_count, method_count = (0, 0,)

            base_cfg = {}

            import ckanext.dgu.testselenium
            for name,cls in inspect.getmembers(sys.modules["ckanext.dgu.testselenium"], inspect.isclass):
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
                    test_name = "%s.%s" % (name, method_name)
                    log.info("Test: %s", test_name)
                    try:
                        method_count += 1
                        log.info("* Test: %s" % method_name)
                        getattr(instance, method_name)()
                    except Exception as e:
                        exception_str = traceback.format_exc(limit=3)
                        error_dict[test_name].append(exception_str)
                        log.exception(e)
                        log.info("Test failed: %s.%s", name, method_name)
                    except AssertionError as e:
                        exception_str = traceback.format_exc(limit=3)
                        error_dict[test_name].append(exception_str)
                        log.exception(e)
                        log.info("Test failed: %s.%s", name, method_name)
                    else:
                        log.info("Test passed: %s", test_name)

        finally:
            # Cleanup
            self.selenium.stop()
            if self.selenium_process:
                log.info("Closing down our local selenium server")
                self.selenium_process.kill()

        log.info("Ran %d tests with %d failures", method_count, len(error_dict))

        if error_dict:
            print 'Errors:'
            print '-' * 50
            for k,v in error_dict.iteritems():
                print 'Test:', k
                for i in v:
                    print i
                print '-' * 50
            sys.exit(1)  # Make sure bail so that we know we have errors


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

