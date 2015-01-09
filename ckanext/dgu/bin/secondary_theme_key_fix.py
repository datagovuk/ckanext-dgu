'''
Fix the secondary theme extras to all have the same key
http://redmine.dguteam.org.uk/issues/1660

e.g.

"theme-secondary": "\"Government\"",
"themes-secondary": "[\"Education\"]",

becomes:

"theme-secondary": "[\"Government\", \"Education\"]",
'''

import json
from optparse import OptionParser

from sqlalchemy import or_

from ckan import model

from ckanext.dgu.bin import common
from running_stats import StatsList


stats = StatsList()


def fix(config_ini, write):
    common.load_config(config_ini)
    common.register_translator()

    if write:
        rev = model.repo.new_revision()
        rev.author = 'script-' + __file__
        # rev.author "script-" prefix stops the changes appearing in the
        # publisher_activity report

    packages = model.Session.query(model.Package) \
                    .filter_by(state='active') \
                    .join(model.PackageExtra) \
                    .filter_by(state='active') \
                    .filter(or_(model.PackageExtra.key == 'theme-secondary',
                                model.PackageExtra.key == 'themes-secondary'))\
                    .all()

    for pkg in packages:
        withs = pkg.extras.get('themes-secondary')
        withouts = pkg.extras.get('theme-secondary')
        if withs and not withouts:
            print stats.add('Dropped the s', pkg.name)
            if write:
                pkg.extras['theme-secondary'] = withs
                del pkg.extras['themes-secondary']
        elif withouts and not withs:
            print stats.add('Already without an s', pkg.name)
        elif withouts and withs:
            print stats.add('Merged the two', pkg.name)
            withouts = json.loads(withouts)
            if isinstance(withouts, basestring):
                withouts = [withouts]
            withs = set(json.loads(withs))
            mix = json.dumps(withouts + list((withs - set(withouts))))
            if write:
                pkg.extras['theme-secondary'] = mix
                del pkg.extras['themes-secondary']
    if write:
        model.Session.commit()

    print stats.report()


usage = __doc__.split('\n\n')[0] + '''

Usage:

    python secondary_theme_key_fix.py <CKAN config ini filepath> [--write]
'''

if __name__ == '__main__':
    parser = OptionParser(usage=usage)
    parser.add_option("-w", "--write",
                      action="store_true",
                      dest="write",
                      default=False,
                      help="write the changes")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error('Should be 1 argument, not %s' % len(args))
    config_ini = args[0]
    fix(config_ini, options.write)
