'''Tool that removes all sysadmins as admins of publishers
'''
import sys

from ckanext.dgu.bin import common
from ckanext.dgu.bin.running_stats import StatsList


def remove_admins():
    from ckan import model

    admin_ids = [i[0] for i in model.Session.query(model.User.id).filter_by(sysadmin=True).all()]

    members = model.Session.query(model.Member)\
                .filter_by(table_name='user', capacity='admin', state='active')\
                .filter(model.Member.table_id.in_(admin_ids))

    print "There are %s memberships to be deleted" % members.count()

    members.update({'state': 'deleted'}, synchronize_session='fetch')

    model.Session.commit()


if __name__ == '__main__':
    usage = __doc__ + """
usage:

%prog <ckan.ini>
"""
    if len(sys.argv) < 2:
        print usage
        sys.exit("Wrong number of args")
    config_filepath = sys.argv[1]
    print 'Loading CKAN config...'
    common.load_config(config_filepath)
    common.register_translator()
    print 'Done'
    remove_admins()

