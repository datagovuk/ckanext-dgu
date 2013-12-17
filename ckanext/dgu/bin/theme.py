from optparse import OptionParser
from collections import defaultdict
import logging

from sqlalchemy import or_, not_
import nltk

import common
from running_stats import StatsList

# NB put no CKAN imports here, or logging breaks

def learn(options):
    '''Analyse datasets that are already categorise to find out which words
    associate with which theme.
    '''
    from ckanext.dgu.lib.theme import Themes
    level = 1
    freq_dists = {}
    fd_by_fraction = defaultdict(list)
    count = 0
    for theme in Themes.instance().data:
        count += 1
        if count == 30:
            break
        options.theme = theme
        freq_dist = get_freq_dist(options, level)
        print '%s: %r' % (theme, freq_dist)
        freq_dists[theme] = freq_dist
        if not len(freq_dist):
            continue
        max_freq = freq_dist[freq_dist.max()]
        freq_fraction_threshold = 0.0
        for word, freq in freq_dist.items():
            freq_fraction = float(freq)/max_freq
            if freq_fraction < freq_fraction_threshold:
                break
            fd_by_fraction[word].append((freq_fraction, theme, freq))

    stats = StatsList()
    stats.report_value_limit = 1000
    unique_words = defaultdict(list)  # theme: [word, ...]
    for word, counts in fd_by_fraction.items():
        if len(counts) == 1:
            print stats.add('unique', '%s %s' % (word, counts[0][1]))
            unique_words[counts[0][1]].append('%s (%s)' % (word, counts[0][2]))
            continue
        sorted_counts = sorted(counts, key=lambda tup: -tup[0])
        winning_margin = sorted_counts[0][0] - sorted_counts[1][0]
        print stats.add('margin %.1f' % winning_margin, '%s %s-%s' % (word, sorted_counts[0][1], sorted_counts[1][1]))
    print 'Unique words:'
    for theme, words in unique_words.items():
        print '%s: %s' % (theme, ' '.join(words))
    print 'Summary:'
    print stats.report()

def get_freq_dist(package_options, level):
    '''Find all the words in the packages and return the freq dist of them.'''
    from ckanext.dgu.lib.theme import dictize_package_nice, package_text, normalize_text
    packages = get_packages(publisher=package_options.publisher,
                            theme=package_options.theme,
                            uncategorized=package_options.uncategorized,
                            limit=options.limit)

    text = []
    for pkg in packages:
        # print 'Dataset: %s %s %s' % (pkg.name, pkg.extras.get(PRIMARY_THEME), pkg.extras.get(SECONDARY_THEMES))
        pkg = dictize_package_nice(pkg)
        text.append(package_text(pkg, level))
    words = []
    text = ' '.join(text)
    words = normalize_text(text)
    return nltk.FreqDist(words)


def categorize(options, test=False):
    from ckanext.dgu.lib.theme import categorize_package, PRIMARY_THEME

    stats = StatsList()
    stats.report_value_limit = 1000

    if options.dataset:
        pkg = model.Package.get(options.dataset)
        assert pkg
        packages = [pkg]
    else:
        if test:
            theme = True
        else:
            theme = False
        packages = get_packages(publisher=options.publisher,
                                theme=theme,
                                uncategorized=options.uncategorized,
                                limit=options.limit)

    themes_to_write = {}  # pkg_name:themes

    for pkg in packages:
        print 'Dataset: %s' % pkg.name
        themes = categorize_package(pkg, stats)
        if options.write and not pkg.extras.get(PRIMARY_THEME) and themes:
            themes_to_write[pkg.name] = themes

    print 'Categorize summary:'
    print stats.report()

    if options.write:
        write_themes(themes_to_write)

def write_themes(themes_to_write):
    from ckanext.dgu.lib.theme import PRIMARY_THEME, SECONDARY_THEMES

    rev = model.repo.new_revision()
    rev.author = 'autotheme'
    print 'Writing %i datesets\' themes' % len(themes_to_write)
    for pkg_name, themes in themes_to_write.items():
            #print 'WRITE %s %r' % (pkg_name, themes)
            pkg = model.Package.get(pkg_name)
            pkg.extras[PRIMARY_THEME] = themes[0]
            if len(themes) > 1:
                pkg.extras[SECONDARY_THEMES] = '["%s"]' % themes[1]
    model.repo.commit_and_remove()

def recategorize(options):
    from ckanext.dgu.lib.theme import (categorize_package, PRIMARY_THEME,
            SECONDARY_THEMES, Themes)

    stats = StatsList()
    stats.report_value_limit = 1000

    if options.dataset:
        pkg = model.Package.get(options.dataset)
        assert pkg
        packages = [pkg]
    else:
        packages = get_packages(publisher=options.publisher,
                                theme=None,
                                uncategorized=options.uncategorized,
                                limit=options.limit)

    # process the list of themes we are interested in setting on packages
    themes = Themes.instance()
    if options.theme:
        theme_filter = set(options.theme.split(','))
        for theme in theme_filter:
            assert theme in themes.data, '"%s" not in %r' % (theme, themes.data)
    else:
        theme_filter = themes.data

    themes_to_write = {}  # pkg_name:themes

    for pkg in packages:
        print 'Dataset: %s' % pkg.name
        themes = categorize_package(pkg)
        existing_theme = pkg.extras.get(PRIMARY_THEME)
        pkg_identity = '%s (%s)' % (pkg.name, existing_theme)
        if not themes:
            print stats.add('Cannot decide theme', pkg_identity)
            continue
        if themes[0] not in theme_filter:
            print stats.add('Not interested in theme', pkg_identity)
            continue
        if existing_theme == themes[0]:
            print stats.add('Theme unchanged %s' % themes[0], pkg_identity)
            continue
        print stats.add('Recategorized to %s' % themes[0], pkg_identity)
        if options.write:
            themes_to_write[pkg.name] = themes

    print 'Recategorize summary:'
    print stats.report()

    if options.write:
        write_themes(themes_to_write)

def get_packages(publisher=None, theme=None, uncategorized=False, limit=None):
    from ckan import model
    from ckanext.dgu.lib.theme import PRIMARY_THEME, Themes
    packages = model.Session.query(model.Package) \
                .filter_by(state='active')
    if options.publisher:
        publisher_ = model.Group.get(publisher)
        packages = packages.filter_by(owner_org=publisher_.id)
    if uncategorized:
        theme = 'uncategorized'
    if theme is True:
        # only packages with a theme
        packages = packages.join(model.PackageExtra) \
                            .filter_by(key=PRIMARY_THEME) \
                            .filter(model.PackageExtra.value != None) \
                            .filter(model.PackageExtra.value != '') \
                            .filter_by(state='active')
    elif theme == 'uncategorized':
        # only packages not of a known theme
        themes = model.Session.query(model.PackageExtra) \
                            .filter_by(key=PRIMARY_THEME) \
                            .filter_by(state='active') \
                            .subquery()
        valid_themes = Themes.instance().data.keys()
        packages = packages.outerjoin(themes, themes.c.package_id==model.Package.id) \
                            .filter(not_(themes.c.value.in_(valid_themes)))
        import pdb; pdb.set_trace()
    elif theme:
        # only packages of a particular theme
        packages = packages.join(model.PackageExtra) \
                            .filter_by(key=PRIMARY_THEME) \
                            .filter(model.PackageExtra.value == theme) \
                            .filter_by(state='active')
    elif theme == False:
        # only packages without a theme
        themes = model.Session.query(model.PackageExtra) \
                            .filter_by(key=PRIMARY_THEME) \
                            .filter_by(state='active') \
                            .subquery()
        packages = packages.outerjoin(themes, themes.c.package_id==model.Package.id) \
                            .filter(or_(themes.c.value == None,
                                        themes.c.value == ''))
    elif theme is None:
        # all packages
        pass
    total_count = packages.count()
    if limit is not None:
        packages = packages.limit(int(limit))
    packages = packages.all()
    print 'Datasets: %s/%s' % (len(packages), total_count)
    return packages



if __name__ == '__main__':
    usage = """Derives a theme for each dataset
    usage: %prog [options] <ckan.ini> <command>
Commands:
    learn - look at datasets already with themes and show the key words
    test - try categorizing datasets that already have themes to see how well it does
    categorize - categorize datasets without themes
    recategorize - recategorize datasets"""
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-p', '--publisher', dest='publisher')
    parser.add_option('-t', '--theme', dest='theme',
            help="Comma separated (for recategorize command only)")
    parser.add_option('--uncategorized',
                      action="store_true", dest="uncategorized",
                      help='Look at datasets with no theme or a bad theme')
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    parser.add_option('--limit', dest='limit')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments (%i)' % len(args))
    config_ini, command = args
    commands = ('learn', 'test', 'categorize', 'recategorize')
    if command not in commands:
        parser.error('Command %s should be one of: %s' % (command, commands))
    print 'Loading CKAN config...'
    common.load_config(config_ini)
    common.register_translator()
    print 'Done'
    # Setup logging to print debug out for theme stuff only
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.WARNING)
    themeLogger = logging.getLogger('ckanext.dgu.lib.theme')
    themeLogger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    themeLogger.addHandler(handler)
    #logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    from ckan import model
    if command == 'learn':
        learn(options)
    elif command == 'test':
        categorize(options, test=True)
    elif command == 'categorize':
        categorize(options)
    elif command == 'recategorize':
        recategorize(options)
    else:
        raise NotImplemented()
