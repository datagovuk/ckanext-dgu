#!/usr/bin/env python

import os
import sys
import logging

from sqlalchemy import create_engine, engine_from_config
from sqlalchemy import Table, MetaData, types, Column
from datetime import date
import pylons
from pylons import config
from pylons.i18n import _
from pylons.i18n.translation import set_lang
import ckan.model as model
from ckan.logic import get_action

def load_config(path):
    import paste.deploy
    from paste.registry import Registry
    from command import MockTranslator

    conf = paste.deploy.appconfig('config:' + os.path.abspath(path))

    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)

    registry=Registry()
    registry.prepare()
    translator_obj = MockTranslator()
    registry.register(pylons.translator, translator_obj)


def run_report_specific(config_ini_filepath, with_desc=False):
    # Shows problem described in issue #146
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    context = {'model': model, 'session': model.Session,
               'user': None, 'extras_as_string': True, 'for_view': False}
    pkg_dict = get_action('package_show')(context, {'id': 'disclosure-ministerial-hospitality-received-scotland-office'})

    import pprint
    members = model.Session.query(model.Member).filter(model.Member.table_id==pkg_dict['id']).all()
    pprint.pprint( members)

    member_rev = model.Session.query(model.MemberRevision).filter(model.MemberRevision.table_id==pkg_dict['id']).all()
    pprint.pprint (member_rev)


def run_report_all_multi(config_ini_filepath, with_desc=False):
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    context = {'model': model, 'session': model.Session,
               'user': None, 'extras_as_string': True, 'for_view': False}
    packagenum = model.Session.query(model.Package).filter(model.Package.state=='active').count()
    packages = model.Session.query(model.Package).filter(model.Package.state=='active').all()
    i = 0
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    for package in packages:
        i = i + 1
        print '%d/%d\r' % (i,packagenum),
        pkg_dict = get_action('package_show')(context, {'id': package.id})
        l = len(pkg_dict['groups'])
        if l != 1:
            print "%s (%d)" % (package.name, len(pkg_dict['groups']))


def run_report(config_ini_filepath, with_desc=False):
    load_config(config_ini_filepath)
    engine = engine_from_config(config, 'sqlalchemy.')

    def display_package(p,c,d,g,wd):
        print "=" * 80
        print "%s\t%d" % (p,c,)
        print "=" * 80
        if with_desc:
            if g:
                print "\nGroups: %s" % g
            print "\n%s" % d.encode('utf-8','ignore')

            print "-" * 80

    packagelist = []
    packages = model.Session.query(model.Package).filter(model.Package.state=='active').all()
    for package in packages:
        grps = package.get_groups('organization')
        c = len(grps)
        if not c == 1:
            display_package(package.name, c, package.notes,
                            [g.name for g in grps],
                            with_desc)


def usage():
    print """
Usage:
   Finds out interesting things about publishers, like which datasets have two and
   which have none.

    python publisher_info.py <path to ini file>
    """

if __name__ == '__main__':
    if len(sys.argv) == 2:
        cmd, config_ini = sys.argv
    elif len(sys.argv) == 3:
        cmd, config_ini, with_desc = sys.argv
        with_desc = with_desc.lower() in ["true", "yes", "t", "y" ]
    else:
        usage()
        sys.exit(0)

    run_report(config_ini, with_desc)
