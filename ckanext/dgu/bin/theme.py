from optparse import OptionParser
import os.path
import simplejson as json
import codecs
import re
from collections import defaultdict

from sqlalchemy import or_
# Use nltk.download() to get the 'stopwords' corpus
import nltk
from nltk.corpus import stopwords
import common
from running_stats import StatsList

PRIMARY_THEME = 'theme-primary'
SECONDARY_THEMES = 'themes-secondary'

class Themes(object):
    def __init__(self):
        themes_filepath = os.path.abspath(os.path.join(__file__, '../../themes.json'))
        assert os.path.exists(themes_filepath), themes_filepath
        print 'Reading themes.json'
        with codecs.open(themes_filepath, encoding='windows-1252') as f:
            themes_json = f.read()
        themes_list = json.loads(themes_json)
        self.data = {}
        for theme_dict in themes_list:
            name = theme_dict.get('stored_as') or theme_dict['title']
            self.data[name] = theme_dict
        print 'Done'

def learn(options):
    from ckan import model

    themes = Themes()
    level = 1
    freq_dists = {}
    fd_by_fraction = defaultdict(list)
    count = 0
    for theme in themes.data:
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
            fd_by_fraction[word].append((freq_fraction, theme))

    stats = StatsList()
    for word, counts in fd_by_fraction.items():
        if len(counts) == 1:
            print stats.add('unique', '%s %s' % (word, counts[0][1]))
            continue
        sorted_counts = sorted(counts, key=lambda tup: -tup[0])
        winning_margin = sorted_counts[0][0] - sorted_counts[1][0]
        print stats.add('margin %.1f' % winning_margin, '%s %s-%s' % (word, sorted_counts[0][1], sorted_counts[1][1]))
    print stats.report()

def get_freq_dist(package_options, level):
    packages = get_packages(publisher=package_options.publisher,
                            theme=package_options.theme,
                            limit=options.limit)

    text = []
    for pkg in packages:
        # print 'Dataset: %s %s %s' % (pkg.name, pkg.extras.get(PRIMARY_THEME), pkg.extras.get(SECONDARY_THEMES))
        text.append(package_text(pkg, level))
    words = []
    text = ' '.join(text)
    words = [normalize_token(w) for w in split_words(text)]
    return nltk.FreqDist(words)

porter = None

def split_words(sentence, remove_stop_words=True):
    words = re.findall(r'\w+', sentence, flags=re.UNICODE)
    if remove_stop_words:
        important_words = []
        for word in words:
            if word not in stopwords.words('english'):
                important_words.append(word)
        words = important_words
    return words

def normalize_token(token):
    global porter
    if not porter:
        porter = nltk.PorterStemmer()
    token = porter.stem(token)
    token = re.sub('[^\w]', '', token)
    token = token.lower()
    return token

def categorize(packages):
    from ckan import model

    themes = Themes()
    stats = StatsList()

    if options.dataset:
        packages = [model.Package.get(options.dataset)]
    else:
        packages = get_packages(publisher=options.publisher,
                theme=command=='learn',
                limit=options.limit)

    for pkg in packages:
        print 'Dataset: %s' % pkg.name


def package_text(package, level):
    '''Given a package returns the text in it, from a particular level.
    The first level is the most important - title, followed by less important bits.
    '''
    if level == 0:
        return package.title
    elif level == 1:
        tags = package.get_tags() or []
        tag_text = ' '.join([re.sub('[-_]', ' ', tag.name) for tag in tags])
        return tag_text
    elif level == 2:
        return package.notes or ''

def get_packages(publisher=None, theme=None, limit=None):
    from ckan import model
    packages = model.Session.query(model.Package) \
                .filter_by(state='active')
    if options.publisher:
        publisher_ = model.Group.get(publisher)
        packages = packages.filter_by(owner_org=publisher_.id)
    if theme is True:
        # only packages with a theme
        packages = packages.join(model.PackageExtra) \
                            .filter_by(key=PRIMARY_THEME) \
                            .filter(model.PackageExtra.value != None) \
                            .filter(model.PackageExtra.value != '') \
                            .filter_by(state='active')
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
    categorize - categorize datasets without themes"""
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--dataset', dest='dataset')
    parser.add_option('-p', '--publisher', dest='publisher')
    parser.add_option("-w", "--write",
                      action="store_true", dest="write",
                      help="write the theme to the datasets")
    parser.add_option('--limit', dest='limit')
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error('Wrong number of arguments (%i)' % len(args))
    config_ini, command = args
    commands = ('learn', 'categorize')
    if command not in commands:
        parser.error('Command %s should be one of: %s' % (command, commands))
    print 'Loading CKAN config...'
    common.load_config(config_ini)
    common.register_translator()
    print 'Done'
    from ckan import model
    if command == 'learn':
        learn(options)
    elif command == 'categorize':
        categorize(options)
    else:
        raise NotImplemented()
