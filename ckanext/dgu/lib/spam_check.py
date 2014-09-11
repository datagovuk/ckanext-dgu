from pylons import config

import requests
from requests_oauthlib import OAuth1

import logging

MOLLOM_HAM = 1
MOLLOM_SPAM = 2
MOLLOM_UNSURE = 3


log = logging.getLogger(__name__)

def classify(spam_text):
    classifications = [None, 'ham', 'spam', 'unsure']
    try:
        return classifications.indx(spam_text)
    except ValueError:
        return MOLLOM_UNSURE

def is_spam(content, author=None):
    """
    Checks whether the provided content is spam.  Returns a boolean
    denoted a successful call and a SPAM flag which is one of MOLLOM_HAM,
    MOLLOM_SPAM, MOLLOM_UNSURE.

    It is expected that a failure to retrieve a score will force the
    item into moderation. A flag of MOLLOM_SPAM should mark the item as
    not visible and anything else should be published.
    """
    public_key = config.get('mollom.public.key')
    private_key = config.get('mollom.private.key')

    try:
        params = { 'postBody': content}
        if author:
            params['authorName'] = author.fullname or ''
            params['authorMail'] = author.email

        auth = OAuth1(publicKey, privateKey)

        headers = {'Accept': 'application/json;q=0.8, */*;q=0.5'}

        response = requests.post(mollom_content_url, params, auth=auth, headers=headers)
        cc = response.json()['content']
    except Exception, e:
        log.warning("Failed to perform a spam check with mollom")
        log.exception(e)
        return False, MOLLOM_UNSURE

    log.info("Mollom says: {0}".format(cc))
    return True, classify(cc['spamClassification'])
