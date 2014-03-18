import os.path
import simplejson as json
import codecs
import re
from collections import defaultdict

# Use nltk.download() to get the 'stopwords' corpus
import nltk
from nltk.corpus import stopwords
from nltk.util import bigrams, trigrams

from ckanext.dgu.schema import tag_munge
from ckan import model

log = __import__('logging').getLogger(__name__)

PRIMARY_THEME = 'theme-primary'
SECONDARY_THEMES = 'themes-secondary'

class Themes(object):
    '''Singleton class containing the data from themes.json with a bit of processing.'''
    _instance = None
    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = Themes()
        return cls._instance

    def __init__(self):
        themes_filepath = os.path.abspath(os.path.join(__file__, '../../themes.json'))
        assert os.path.exists(themes_filepath), themes_filepath
        log.debug('Reading themes.json')
        with codecs.open(themes_filepath, encoding='utf8') as f:
            themes_json = f.read()
        themes_list = json.loads(themes_json)
        self.data = {}
        self.topic_words = {}  # topic:theme_name
        self.topic_bigrams = {} # (topicword1, topicword2):theme_name
        self.topic_trigrams = {} # (topicword1, topicword2, topicword3):theme_name
        self.gemet = {}  # gemet_keyword:theme_name
        self.ons = {}  # ons_keyword:theme_name
        self.lga_functions = {} # LGA functions extra
        self.lga_services = {}  # LGA services extra
        for theme_dict in themes_list:
            name = theme_dict.get('stored_as') or theme_dict['title']

            for key in ('topics', 'gemet', 'nscl', 'ons', 'lga_functions', 'lga_services'):
                if key in theme_dict:
                    assert isinstance(theme_dict[key], list), (name, key)

            for topic in theme_dict['topics']:
                words = [normalize_token(word) for word in split_words(topic)]
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
            for function_id in theme_dict.get('lga_functions', []):
                self.lga_functions[function_id] = name
            for service_id in theme_dict.get('lga_services', []):
                self.lga_services[service_id] = name
            self.data[name] = theme_dict
        self.topic_words_set = self.topic_words.viewkeys() # can do set-like operations on it
        self.topic_bigrams_set = self.topic_bigrams.viewkeys()
        self.topic_trigrams_set = self.topic_trigrams.viewkeys()


def normalize_text(text):
    words = [normalize_token(w) for w in split_words(text)]
    words_without_stopwords = [word for word in words
            if word not in stopwords.words('english')]
    return words, words_without_stopwords

def split_words(sentence):
    # remove "," in a number so that "25,000" is treated as one word
    re.sub('(\d+),(\d+)', r'\1\2', sentence)
    words = re.findall(r'\w+', sentence, flags=re.UNICODE)
    return words

# some words change meaning if you reduce them to their stem
stem_exceptions = set(('parking', 'national', 'coordinates', 'granted'))

porter = None
def normalize_token(token):
    global porter
    if not porter:
        porter = nltk.PorterStemmer()
    token = re.sub('[^\w]', '', token)
    token = token.lower()
    if token not in stem_exceptions:
        token = porter.stem(token)
    return token

def dictize_package_nice(pkg):
    # package comes in as dict or an object. Convert both to a convenient dict.
    if isinstance(pkg, model.Package):
        return {'name': pkg.name,
                'title': pkg.title,
                'tags': [tag.name for tag in pkg.get_tags()],
                'notes': pkg.notes,
                'extras': pkg.extras
                }
    else:
        pkg_dict = {'name': pkg['name'],
                    'title': pkg['title'],
                    'notes': pkg['notes'],
                    }
        # Cope with tags as a list of dicts or just a list
        if pkg['tags'] and isinstance(pkg['tags'][0], dict):
            pkg_dict['tags'] = [tag['name'] for tag in pkg['tags']]
        else:
            pkg_dict['tags'] = pkg['tags'][:]
        # Cope with extas as a list of dicts or just a dict
        if pkg['extras'] and isinstance(pkg['extras'], list):
            pkg_dict['extras'] = dict([(extra['key'], extra['value']) for extra in pkg['extras']])
        else:
            pkg_dict['extras'] = dict(pkg['extras'].items())
        return pkg_dict

def categorize_package(pkg, stats=None):
    '''Given a package it does various searching for topic keywords and returns
    its estimate for primary-theme and secondary-theme.

    package - object or dict
    '''
    if stats is None:
        class MockStats:
            def add(self, a, b):
                return '%s: %s' % (a, b)
        stats = MockStats()

    pkg = dictize_package_nice(pkg)
    scores = defaultdict(list)  # theme:[(score, reason), ...]
    score_by_topic(pkg, scores)
    score_by_gemet(pkg, scores)
    score_by_ons_theme(pkg, scores)
    score_by_lga_function(pkg, scores)

    # add up scores
    theme_scores = defaultdict(int)  # theme:total_score
    for theme, theme_scores_ in scores.items():
        for score, reason in theme_scores_:
            theme_scores[theme] += score
    theme_scores = sorted(theme_scores.items(), key=lambda y: -y[1])

    primary_theme = theme_scores[0][0] if scores else None

    current_primary_theme = pkg['extras'].get(PRIMARY_THEME)
    if scores:
        if primary_theme == current_primary_theme:
            log.debug(stats.add('Theme matches', '%s %s %s' % (pkg['name'], primary_theme, theme_scores[0][1])))
        elif current_primary_theme:
            log.debug(stats.add('Misidentified theme', '%s guess=%s shd_be=%s %s' % (pkg['name'], primary_theme, current_primary_theme, theme_scores[0][1])))
        else:
            log.debug(stats.add('Theme where there was none previously', '%s guess=%s %s' % (pkg['name'], primary_theme, theme_scores[0][1])))
    else:
        log.debug(stats.add('No match', pkg['name']))
    return [theme for theme, score in theme_scores[:2]]

def score_by_topic(pkg, scores):
    '''Examines the pkg and adds scores according to topics in it.'''
    themes = Themes.instance()
    for level in range(3):
        pkg_text = package_text(pkg, level)
        words, words_without_stopwords = normalize_text(pkg_text)
        for num_words in (1, 2, 3):
            if num_words == 1:
                ngrams = words_without_stopwords
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
                    if occurrences > 1:
                        reason += ' (%s times)' % occurrences
                    scores[theme].append((score, reason))
                    log.debug(' %s %s %s', theme, score, reason)

def score_by_gemet(pkg, scores):
    if pkg['extras'].get('UKLP') != 'True':
        return
    themes = Themes.instance()
    for tag in pkg['tags']:
        tag = normalize_keyword(tag)
        if tag in themes.gemet:
            theme = themes.gemet[tag]
            reason = '%s matched GEMET keyword' % tag
            score = 40 # needs to be high for e.g. urban-rural-classification-2011-12
            scores[theme].append((score, reason))
            log.debug(' %s %s %s', theme, score, reason)
        else:
            log.debug(' Non-GEMET keyword: %s', tag)

def score_by_ons_theme(pkg, scores):
    # There are 11 'Old ONS themes' e.g.: 'Agriculture and Environment', 'Business and Energy'
    # http://www.statistics.gov.uk/hub/browse-by-theme/index.html
    #
    # and there are set to be 4 'New ONS themes' e.g. 'Business, Trade and Industry'
    # which break down further, that we need to look at too.
    # http://digitalpublishing.ons.gov.uk/2013/12/05/no-longer-taxing-we-hope/
    if pkg['extras'].get('external_reference') != 'ONSHUB':
        return
    themes = Themes.instance()
    for tag in pkg['tags']:
        tag = tag_munge(tag)
        if tag in themes.ons:
            theme = themes.ons[tag]
            reason = '%s matched ONS keyword' % tag
            score = 10
            scores[theme].append((score, reason))
            log.debug(' %s %s %s' % (theme, score, reason))

def score_by_lga_function(pkg, scores):
    ''' Grants a score based on the presence of an LGA function
    extra. This is set by the LGA harvester and will be a list of
    URLS to the fixed function list at
    http://standards.esd.org.uk/?uri=list%2Ffunctions of the form
    http://id.esd.org.uk/function/1 '''
    if not pkg['extras'].get('functions', False):
        return

    themes = Themes.instance()
    for furl in pkg['extras'].get('functions'):
        # function id is the last part of the URL
        fid = furl.split('/')[-1]
        if fid in themes.lga_functions:
            theme = themes.lga_functions[fid]
            reason = "Function ID was matched"
            score = 100
            scores[theme].append((score,reason,))
            log.debug("%s %s %s", theme, score, reason)
        else:
            log.debug("A non-LGA function identifier was found")

def score_by_lga_service(pkg, scores):
    ''' Grants a score based on the presence of an LGA services
    extra. This is set by the LGA harvester and will be a list of
    URLS to the fixed services list at
    http://standards.esd.org.uk/?uri=list%2Fservices of the form
    http://id.esd.org.uk/service/1 '''
    if not pkg['extras'].get('services', False):
        return

    themes = Themes.instance()
    for surl in pkg['extras'].get('services'):
        # service id is the last part of the URL
        sid = surl.split('/')[-1]
        if sid in themes.lga_services:
            theme = themes.lga_services[fid]
            reason = "Service ID was matched"
            score = 10
            scores[theme].append((score,reason,))
            log.debug("%s %s %s", theme, score, reason)
        else:
            log.debug("A non-LGA service identifier was found")

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
        return package['title']
    elif level == 1:
        tag_text = ' '.join([re.sub('[-_]', ' ', tag) for tag in package['tags']])
        return tag_text
    elif level == 2:
        return package['notes'] or ''

