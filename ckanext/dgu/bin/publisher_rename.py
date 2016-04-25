'''
Renames a publisher. This isn't possible with the Web UI since reindexing lots of datasets times out a web request.
'''
# Related to:
# * http://redmine.dguteam.org.uk/issues/575
# * https://github.com/ckan/ideas-and-roadmap/issues/66

# Code derived from:
# https://github.com/datagovuk/ckan/blob/release-v1.7.1-dgu/ckan/lib/cli.py#L822

import argparse

import common


class PublisherRenamer(object):
    def rename(self, old_name, new_name, new_title=None):
        """ Changes the slug for the group """
        import ckan.model as model
        import ckan.lib.search as search

        print "Converting '{0}' to '{1}'".format(old_name, new_name)

        existing = model.Group.by_name(new_name)
        if existing:
            print "'{0}' is already in user, please choose another name".format(new_name)

        group = model.Group.by_name(old_name)
        if not group:
            print "Group {g} not found".format(g=old_name)
            return

        model.repo.new_revision()
        group.name = new_name
        x = sum(1 for k in group.extras.keys() if k.startswith('previous-name-'))
        group.extras['previous-name-%d' % (x+1)] = old_name
        if new_title:
            group.extras['previous-title'] = group.title
            group.title = new_title
        group.save()

        print "Updating search index ...."
        members = model.Session.query(model.Member).filter(model.Member.group_id==group.id).\
            filter(model.Member.state=='active').filter(model.Member.table_name=='package')
        for member in members:
            search.rebuild(member.table_id)

        self._display_group(group)

    def _display_group(self, group):
        """ Displays some useful information about the group """

        import ckan.model as model

        print '*' * 40, "info"
        print "Title:       {title}".format(title=group.title)
        print "Type:        {type}".format(type=group.type or "default")
        print "Name:        {name}".format(name=group.name)
        print "Description: {desc}".format(desc=group.description)
        print "Image URL:   {u}".format(u=group.image_url)
        print "Status:      {s}".format(s=group.state)

        print '*' * 40, "stats"
        admin_count = group.members_of_type(model.User, 'admin').count()
        print "Admins: {uc}".format(uc=admin_count)
        if admin_count:
            print "    -> ",
            print ', '.join(u.name for u in group.members_of_type(model.User, 'admin').all())

        editor_count = group.members_of_type(model.User, 'editor').count()
        print "Editors: {uc}".format(uc=editor_count)
        if editor_count:
            print "    -> ",
            print ', '.join(u.name for u in group.members_of_type(model.User, 'editor').all())

        print "Dataset count: {dc}".format(dc=group.members_of_type(model.Package).count())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config',
                        help='CKAN config .ini filepath')
    parser.add_argument('old_name', metavar='old_name')
    parser.add_argument('new_name', metavar='new-name')
    parser.add_argument('-t', '--title',
                        help='Title to set')
    args = parser.parse_args()

    common.load_config(args.config)
    common.register_translator()

    PublisherRenamer().rename(args.old_name, args.new_name, args.title)
