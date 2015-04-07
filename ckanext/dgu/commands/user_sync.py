import logging

from ckan.lib.cli import CkanCommand

from ckanext.dgu.bin.running_stats import StatsList

stats = StatsList()


class UserSync(CkanCommand):
    """
    Syncs the CKAN user details with the master copy in Drupal
    """
    summary = __doc__.strip().split('\n')[0]
    usage = '\n' + __doc__
    max_args = 0
    min_args = 0

    def __init__(self, name):
        super(UserSync, self).__init__(name)

        self.parser.add_option('-w', '--write',
                               dest='write', action='store_true',
                               help='Write the changes to the db')

    def command(self):
        self._load_config()
        self.log = logging.getLogger(__name__)
        self.log.info('Database access initialised')

        self.sync(write=self.options.write)

    def sync(self, write):
        from ckan import model
        from ckanext.dgu.drupalclient import DrupalClient, DrupalRequestError
        from ckanext.dgu.authentication.drupal_auth import DrupalUserMapping
        log = self.log
        update_keys = set(('email', 'fullname'))
        drupal = DrupalClient()
        users = model.Session.query(model.User)\
                     .filter_by(state='active')\
                     .filter(model.User.name.like('user_d%'))\
                     .all()
        log.info('Drupal users in CKAN: %s', len(users))
        for user in users:
            drupal_user_id = DrupalUserMapping.ckan_user_name_to_drupal_id(user.name)
            try:
                drupal_user = drupal.get_user_properties(drupal_user_id)
            except DrupalRequestError, e:
                if 'There is no user with ID' in str(e):
                    log.info(stats.add('Removed deleted user',
                                       '%s %s' % (drupal_user_id, user.fullname)))
                    if write:
                        user.delete()
                    continue
                elif 'Access denied for user' in str(e):
                    log.info(stats.add('Removed blocked user',
                                       '%s %s' % (drupal_user_id, user.fullname)))
                    if write:
                        user.delete()
                    continue
                raise
            DrupalRequestError
            user_dict = DrupalUserMapping.drupal_user_to_ckan_user(drupal_user)
            user_changed = False
            for key in update_keys:
                if getattr(user, key) != user_dict[key]:
                    log.info(stats.add(
                        'Updating field %s' % key,
                        '%s %s %s->%s' % (drupal_user_id, user.fullname,
                                          getattr(user, key), user_dict[key])))
                    if write:
                        setattr(user, key, user_dict[key])
                    user_changed = True
            if not user_changed:
                log.info(stats.add('Unchanged user',
                                   '%s %s' % (drupal_user_id, user.fullname)))
        log.info(stats.report())
        if write:
            log.info('Writing...')
            model.repo.commit_and_remove()
            log.info('...done')
