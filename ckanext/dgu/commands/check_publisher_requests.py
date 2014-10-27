from paste.script.command import Command

from ckan import model
from ckan.lib.cli import CkanCommand
from sqlalchemy import engine_from_config, Table, MetaData, Column, Integer, String
from sqlalchemy.orm import mapper, relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from pylons import config

from ckanext.dgu.model.publisher_request import PublisherRequest

class CheckRequests(CkanCommand):
    # Parser configuration
    summary = "--NO SUMMARY--"
    usage = "--NO USAGE--"
    group_name = "myapp"
    #parser = Command.standard_parser(verbose=False)

    def command(self):
        self._load_config()
        engine = engine_from_config(config, 'sqlalchemy.')

        for req in model.Session.query(PublisherRequest).all():
            print req.decision
            user = model.Session.query(model.User).filter(model.User.name==req.user_name).one()
            group = model.Session.query(model.Group).filter(model.Group.name==req.group_name).one()
            if user.is_in_group(group.id):
                req.decision = True
            model.Session.commit()
