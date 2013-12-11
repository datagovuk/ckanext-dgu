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
from nltk.util import bigrams, trigrams
import common
from running_stats import StatsList
from ckanext.dgu.schema import tag_munge

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
        self.topic_words = {}  # topic:theme_name
        self.topic_bigrams = {} # (topicword1, topicword2):theme_name
        self.topic_trigrams = {} # (topicword1, topicword2, topicword3):theme_name
        self.gemet = {}  # gemet_keyword:theme_name
        self.ons = {}  # ons_keyword:theme_name
        for theme_dict in themes_list:
            name = theme_dict.get('stored_as') or theme_dict['title']

            for key in ('topics', 'gemet', 'nscl', 'ons'):
                if key in theme_dict:
                    assert isinstance(theme_dict[key], list), (name, key)

            for topic in theme_dict['topics']:
                words = [normalize_token(word) for word in topic.split()]
                if len(words) == 1:
                    self.topic_words[words[0]] = name
                elif len(words) == 2:
                    self.topic_bigrams[tuple(words)] = name
                elif len(words) == 3:
                    self.topic_trigrams[tuple(words)] = name
                else:
                    assert 0, 'Too many words in topic: %s' % topic

            for gemet_keyword in theme_dict.get('gemet', []):
                self.gemet[normalize_keyword(gemet_keyword)] = name
            for ons_keyword in theme_dict.get('nscl', []) + theme_dict.get('ons', []):
                self.ons[tag_munge(ons_keyword)] = name
            self.data[name] = theme_dict
        self.topic_words_set = self.topic_words.viewkeys() # can do set-like operations on it
        self.topic_bigrams_set = self.topic_bigrams.viewkeys()
        self.topic_trigrams_set = self.topic_trigrams.viewkeys()
        print 'Done'


def learn(options):
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
    packages = get_packages(publisher=package_options.publisher,
                            theme=package_options.theme,
                            limit=options.limit)

    text = []
    for pkg in packages:
        # print 'Dataset: %s %s %s' % (pkg.name, pkg.extras.get(PRIMARY_THEME), pkg.extras.get(SECONDARY_THEMES))
        text.append(package_text(pkg, level))
    words = []
    text = ' '.join(text)
    words = normalize_text(text)
    return nltk.FreqDist(words)

porter = None

def normalize_text(text):
    words = [normalize_token(w) for w in split_words(text)]
    return words

def split_words(sentence, remove_stop_words=True):
    # remove "," in a number
    re.sub('(\d+),(\d+)', r'\1\2', sentence)
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

def categorize(options, test=False):
    themes = Themes()
    stats = StatsList()
    stats.report_value_limit = 3000

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
                limit=options.limit)

    for pkg in packages:
        print 'Dataset: %s' % pkg.name
        scores = defaultdict(list)  # theme:[(score, reason), ...]
        score_by_topic(pkg, scores, themes)
        score_by_gemet(pkg, scores, themes)
        score_by_ons_theme(pkg, scores, themes)

        # add up scores
        theme_scores = defaultdict(int)  # theme:total_score
        for theme, theme_scores_ in scores.items():
            for score, reason in theme_scores_:
                theme_scores[theme] += score
        theme_scores = sorted(theme_scores.items(), key=lambda y: -y[1])

        primary_theme = theme_scores[0][0] if scores else None

        current_primary_theme = pkg.extras.get(PRIMARY_THEME)
        if scores:
            if primary_theme == current_primary_theme:
                print stats.add('Theme matches', '%s %s %s' % (pkg.name, primary_theme, theme_scores[0][1]))
            elif current_primary_theme:
                print stats.add('Misidentified theme', '%s guess=%s shd_be=%s %s' % (pkg.name, primary_theme, current_primary_theme, theme_scores[0][1]))
            else:
                print stats.add('Theme where there was none previously', '%s guess=%s %s' % (pkg.name, primary_theme, theme_scores[0][1]))
        else:
            print stats.add('No match', pkg.name)
    print stats.report()

def score_by_topic(pkg, scores, themes):
    '''Examines the pkg and adds scores according to topics in it.'''
    for level in range(3):
        pkg_text = package_text(pkg, level)
        words = normalize_text(pkg_text)
        for num_words in (1, 2, 3):
            if num_words == 1:
                ngrams = words
                topic_ngrams = themes.topic_words
                topic_ngrams_set = themes.topic_words_set
            elif num_words == 2:
                ngrams = bigrams(words)
                topic_ngrams = themes.topic_bigrams
                topic_ngrams_set = themes.topic_bigrams_set
            elif num_words == 3:
                ngrams = trigrams(words)
                topic_ngrams = themes.topic_trigrams
                topic_ngrams_set = themes.topic_trigrams_set
            matching_ngrams = set(ngrams) & topic_ngrams_set
            if matching_ngrams:
                for ngram in matching_ngrams:
                    occurrences = ngrams.count(ngram)
                    score = (3-level) * occurrences * num_words
                    theme = topic_ngrams[ngram]
                    ngram_printable = ' '.join(ngram) if isinstance(ngram, tuple) else ngram
                    reason = '"%s" matched %s' % (ngram_printable, LEVELS[level])
                    if occurrences:
                        reason += ' num=%s' % occurrences
                    scores[theme].append((score, reason))
                    print ' %s %s %s' % (theme, score, reason)

def score_by_gemet(pkg, scores, themes):
    if pkg.extras.get('UKLP') != 'True':
        return
    for tag_obj in pkg.get_tags():
        tag = normalize_keyword(tag_obj.name)
        if tag in themes.gemet:
            theme = themes.gemet[tag]
            reason = '%s matched GEMET keyword' % tag
            score = 10
            scores[theme].append((score, reason))
            print ' %s Gemet:%s %s' % (theme, score, reason)
        else:
            print ' Non-GEMET keyword: %s' % tag

def score_by_ons_theme(pkg, scores, themes):
    # There are 11 'Old ONS themes' e.g.: 'Agriculture and Environment', 'Business and Energy'
    # http://www.statistics.gov.uk/hub/browse-by-theme/index.html
    #
    # and there are set to be 4 'New ONS themes' e.g. 'Business, Trade and Industry'
    # which break down further, that we need to look at too.
    # http://digitalpublishing.ons.gov.uk/2013/12/05/no-longer-taxing-we-hope/
    if pkg.extras.get('external_reference') != 'ONSHUB':
        return
    for tag_obj in pkg.get_tags():
        tag = tag_munge(tag_obj.name)
        if tag in themes.ons:
            theme = themes.ons[tag]
            reason = '%s matched ONS keyword' % tag
            score = 10
            scores[theme].append((score, reason))
            print ' %s ONS:%s %s' % (theme, score, reason)

def normalize_keyword(keyword):
    name = keyword.lower()
    # take out not-allowed characters
    name = re.sub('[^a-z0-9]', '', name)
    # remove double spaces
    name = re.sub('\s+', ' ', name)
    return name

LEVELS = {0: 'title', 1: 'tags', 2: 'description'}
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
    test - try categorizing datasets that already have themes to see how well it does
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
    commands = ('learn', 'test', 'categorize')
    if command not in commands:
        parser.error('Command %s should be one of: %s' % (command, commands))
    print 'Loading CKAN config...'
    common.load_config(config_ini)
    common.register_translator()
    print 'Done'
    from ckan import model
    if command == 'learn':
        learn(options)
    elif command == 'test':
        categorize(options, test=True)
    elif command == 'categorize':
        categorize(options)
    else:
        raise NotImplemented()
