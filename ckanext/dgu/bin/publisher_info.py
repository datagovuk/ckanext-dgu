#!/usr/bin/env python

import os
import sys
import logging

from sqlalchemy import create_engine, engine_from_config
from sqlalchemy import Table, MetaData, types, Column
from datetime import date
from pylons import config

import ckan.model as model

def load_config(path):
    import paste.deploy
    conf = paste.deploy.appconfig('config:' + os.path.abspath(path))

    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)


def run_report(config_ini_filepath):
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    packages_too_many = []
    packages_not_enough = []
    packages = model.Session.query(model.Package).filter(model.Package.state=='active').all()
    for package in packages:
        grps = package.get_groups('publisher')
        c = len(grps)
        if c == 0:
            packages_not_enough.append(package.name)
        elif c > 1:
            packages_too_many.append((package.name, c,))

    print "\nPackages with too many publishers (%d)" % len(packages_too_many)
    print "---------------------------------"
    for p,c in packages_too_many:
        print "%s\t%d" % (p,c,)

    print "\nPackages with no publishers (%d)" % len(packages_not_enough)
    print "---------------------------"
    print "\n".join(packages_not_enough)

def usage():
    print """
Usage:
   Finds out interesting things about publishers, like which datasets have two and
   which have none.

    python publisher_info.py <path to ini file>
    """

if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit(0)
    cmd, config_ini = sys.argv
    run_report(config_ini)
