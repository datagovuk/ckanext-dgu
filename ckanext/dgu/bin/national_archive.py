'''
For every resource URL that is marked broken, it checks to see if NationalArchives has
a copy we could use instead. Records the results in /tmp/broken_resources.csv and
writes resource_updates.sql with the SQL commands that would change the resource urls.

TODO:
    * change from TaskStatus to the new archival table
    * maybe ignore short-term breakages - e.g. check for 1 month breakage
    * might be better to write revisions for the changes
'''

import csv
import os
import json
import logging
import sys
import requests
import random
from sqlalchemy import engine_from_config
from pylons import config
import time

from running_stats import StatsCount

TMP_FILE = '/tmp/broken_resources.csv'

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

def command(config_ini):
    config_ini_filepath = os.path.abspath(config_ini)
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    logging.config.fileConfig(config_ini_filepath)
    log = logging.getLogger(os.path.basename(__file__))
    global global_log
    global_log = log

    from ckan import model
    model.init_model(engine)

    report()


def report():
    import ckan.model as model

    log = logging.getLogger(__name__)

    stats = StatsCount()
    #stats.increment('Fixable')

    f = open(TMP_FILE, 'w')
    broken_resources = csv.writer(f)

    # Prep
    tasks = model.Session.query(model.TaskStatus)\
        .filter(model.TaskStatus.task_type == 'qa')\
        .filter(model.TaskStatus.key == 'status')\
        .distinct('entity_id')\
        .all()
    for task in tasks:
        d = json.loads(task.error)
        if 'is_broken' in d and d['is_broken']:
            try:
                resource = model.Resource.get(task.entity_id)
                if resource.resource_group.package.extras.get('UKLP', '') == True:
                    # Skipping UKLP datasets
                    continue
            except Exception, e:
                log.error("Resource.get(%s) failed: %s" % (task.entity_id, e))
                continue

            if resource:
                stats.increment('Broken resource')
                broken_resources.writerow([resource.id, resource.url.encode('utf8')])
        del d
    f.close()

    user_agent = {'User-agent': 'data.gov.uk - please contact ross@servercode.co.uk with problems'}


    # TODO, turn this into an actual change to the resource ....
    def make_query(resource_id, new_url):
        q = [
            u"UPDATE resource_revision SET url='%s' WHERE id='%s' and current=true;" % (new_url, resource_id,),
            u"UPDATE resource SET url='%s' WHERE id='%s';" % (new_url, resource_id,)
        ]
        return "\n".join(q)


    output = open('resource_updates.sql', 'w')
    with open(TMP_FILE, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            rid = row[0]
            url = "http://webarchive.nationalarchives.gov.uk/+/" + row[1]

            try:
                req = requests.head(url, headers=user_agent, verify=False)
                if req.status_code == 200:
                    stats.increment('Fixable')
                    output.write(make_query(rid, url))
                else:
                    stats.increment('Not fixable')
            except:
                stats.increment("Broken check")
            time.sleep(random.randint(1,3))


    output.close()

    print '*' * 60, 'Fixability Report'
    print stats.report()


def usage():
    print __doc__ + """
        python ckanext/dgu/bin/resource_link_check.py <CONFIG_FILE>
    """

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit(0)

    command(sys.argv[1])
