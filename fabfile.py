import os
import sys
import logging
import ConfigParser
from fabric.api import *

_LOCALHOST = "localhost"

ADMIN_USERNAME = 'seleniumadmin'
ADMIN_PASSWORD = 'seleniumpassword'
EDITOR_USERNAME = 'seleniumeditor'
EDITOR_PASSWORD = ADMIN_PASSWORD
CREATE_DATASET = 'seleniumdataset'
EDIT_DATASET = 'seleniumdatasetedit'
PUBLISHER = 'seleniumpublisher'

logging.basicConfig(format="%(asctime)s %(levelname)s [%(module)s]: %(message)s", level=logging.INFO)
log = logging.getLogger(__file__)

def run_tests(test="localhost", port=80, create_drupal_user=False):
    global log

    """ The expected entry point into the fab file, should be run either with
        fab run_tests (for localhost) or fab -u co -H co-dev1.dh.bytemark.co.uk run_test:uat1

        The value given to -H is the server where the tests will be run from, and
        the parameter given to run_test, which defaults to localhost is the server
        that the code will test against.

        The tests can be run on dev1 currently, uat1 etc should be added to the list
        below.
    """
    if not test in ['localhost', 'dev1', 'uat1']:  # Need to expand this list
        print "\nSorry I don't know how to test '%s'" % test
        return

    server = _LOCALHOST if test == 'localhost' else 'co-%s.dh.bytemark.co.uk' % test

    if port != 80:
        server = "{server}:{port}".format(server=server, port=port)

    # Setup the environment and prep the db ready for tests.
    init(server)
    setup_tests(server, create_drupal_user)

    try:
        # Run the tests using the paster command
        selenium(server)
    except Exception as se:
        log.error(se)
        sys.exit(1)
    finally:
        # Clear test data.
        try:
            teardown_tests(server, create_drupal_user)
        except Exception as te:
            log.error(te)
            sys.exit(1)

def init(server):
    global log
    """ Setup the env dictionary with the data we need to run """
    env.root = "/home/co/pyenv_dgu/"

    if server.startswith(_LOCALHOST):
        env.runner = local
        env.root = os.path.abspath(os.path.join(__file__, "../../../"))
    else:
        env.runner = run

    env.config = os.path.join(env.root, 'src/ckan/development.ini')
    if not os.path.exists(env.config):
        env.config = os.path.join(env.root, "dgu_as_co_user.ini")

    env.config_target = "/tmp/test_config.ini"
    env.paster = os.path.join(env.root, 'bin/paster')
    log.info("-- Configuration")
    log.info("Root folder is %s" % env.root)
    log.info("Paster is at %s" % env.paster)
    log.info("Test-Config will be at %s" % env.config_target)


def selenium(server):
    selenium_target = "http://%s/data" % server

    # The selenium server will probably be remote, either it
    # will be started on localhost, or already running on dev1.
    cmdline = ["selenium_tests", "run",
               "--configfile=%s" % env.config_target,
               "--target=%s" % selenium_target]

    _run_paster_command( ' '.join(cmdline) , "ckanext-dgu", True)

def setup_tests(server, create_drupal_user):
    """ Add users and groups ready for the tests """
    global log

    log.info("-- Test Setup")

    commands = [
        # Cleanup, just in case we failed previously
        ("dataset removefromgroup %s %s" % (CREATE_DATASET, PUBLISHER), "ckan", False),
        ("dataset removefromgroup %s %s" % (EDIT_DATASET, PUBLISHER), "ckan", False),
        ("group purge %s" % (PUBLISHER), "ckan", False),
        ("dataset purge %s" % (CREATE_DATASET), "ckan", False),
        ("dataset purge %s" % (EDIT_DATASET), "ckan", False),

        # new data
        ("user add %s password=%s" % (ADMIN_USERNAME, ADMIN_PASSWORD), "ckan",False),
        ("user add %s password=%s" % (EDITOR_USERNAME, EDITOR_PASSWORD), "ckan",False),
        ("group add %s Test publisher" % (PUBLISHER), "ckan",False),
        ("group adduser %s %s admin" % (PUBLISHER,ADMIN_USERNAME), "ckan",False),
        ("group adduser %s %s editor" % (PUBLISHER,EDITOR_USERNAME), "ckan",False),
    ]


    for cmd, plugin, critical in commands:
        try:
            _run_paster_command(cmd, plugin=plugin, critical=critical)
        except:
            log.error("Failed to run command '{c}'".format(c=cmd) )

    if create_drupal_user:
        try:
            args = ["user-create", ADMIN_USERNAME, '--password="%s"' % ADMIN_PASSWORD,
                    '--mail="%s@localhost.local"' % ADMIN_USERNAME]
            _run_drush_command(args)

            args = ["user-create", EDITOR_USERNAME, '--password="%s"' % EDITOR_PASSWORD,
                    '--mail="%s@localhost.local"' % EDITOR_USERNAME]
            _run_drush_command(args)
        except Exception as exc:
            print "Failed to run drush command to create a user: %s" % (exc,)

    # Write config file for tests...
    config = ConfigParser.RawConfigParser()
    config.add_section('LoginTests')
    config.set('LoginTests', 'username', ADMIN_USERNAME)
    config.set('LoginTests', 'password', ADMIN_PASSWORD)

    config.add_section('DatasetTests')
    config.set('DatasetTests', 'editor_username', ADMIN_USERNAME)
    config.set('DatasetTests', 'editor_password', ADMIN_PASSWORD)
    config.set('DatasetTests', 'create_name', CREATE_DATASET)
    config.set('DatasetTests', 'edit_name', EDIT_DATASET)

    config.add_section('PublisherTests')
    config.set('PublisherTests', 'publisher', PUBLISHER)
    config.set('PublisherTests', 'editor_username', ADMIN_USERNAME)
    config.set('PublisherTests', 'editor_password', ADMIN_PASSWORD)
    config.set('PublisherTests', 'user_to_add', EDITOR_USERNAME)

    with open(env.config_target, 'wb') as configfile:
        config.write(configfile)

def teardown_tests(server, delete_drupal_user):
    """ Delete users and groups from the database """
    global log
    log.info("--Teardown")

    commands = [
        ("group removeuser %s %s" % (PUBLISHER,ADMIN_USERNAME), "ckan", False),
        ("group removeuser %s %s" % (PUBLISHER,EDITOR_USERNAME), "ckan", False),
        ("user remove %s" % ADMIN_USERNAME,"ckan", False),
        ("user remove %s" % (EDITOR_USERNAME),"ckan", False),
        ("dataset removefromgroup %s %s" % (CREATE_DATASET,PUBLISHER), "ckan", False),
        ("dataset removefromgroup %s %s" % (EDIT_DATASET,PUBLISHER), "ckan", False),
        ("dataset purge %s" % (CREATE_DATASET), "ckan", True),
        ("dataset purge %s" % (EDIT_DATASET), "ckan", True),
        ("group purge %s" % (PUBLISHER), "ckan", True),
    ]

    for cmd, plugin, critical in commands:
        try:
            _run_paster_command(cmd, plugin=plugin, critical=critical)
        except:
            log.error("Failed to run command '{c}'".format(c=cmd) )

    if delete_drupal_user:
        try:
            args = ["user-cancel", ADMIN_USERNAME, "--delete-content"]
            _run_drush_command(args)

            args = ["user-cancel", EDITOR_USERNAME, "--delete-content"]
            _run_drush_command(args)
        except Exception as exc:
            print "Failed to run drush command to delete a user: %s" % (exc,)

    # Delete the temporary configuration file.
    #if os.path.exists(env.config_target):
    #    os.unlink(env.config_target)


def _run_paster_command(args, plugin='ckanext-dgu', critical=False):
    if plugin:
        cmd = "%s --plugin=%s %s -c %s" % (env.paster, plugin, args, env.config)

    with settings(warn_only=True):
        with cd(os.path.join(env.root, 'src/%s' % plugin)):
            result = env.runner(cmd)
            if result.return_code == 1 and critical:
                raise Exception()

def _run_drush_command(args):
    cmd = "drush --yes --root=/var/www/dgu_d7 %s" % ' '.join(args)

    with settings(warn_only=True):
        log.info("Running drush command: %s" % cmd)
        result = env.runner(cmd)
        if result.return_code == 1 and critical:
            raise Exception(cmd)

