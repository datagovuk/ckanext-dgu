from Mollom import MollomAPI
from pylons import config

import logging

MOLLOM_HAM = 1
MOLLOM_SPAM =  2
MOLLOM_UNSURE = 3


log = logging.getLogger(__name__)

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
        mollom_api = MollomAPI(
            publicKey=public_key,
            privateKey=private_key)

        params = { 'postBody': content}
        if author:
            params['authorName'] = author.fullname or ''
            params['authorMail'] = author.email

        cc = mollom_api.checkContent(**params)
    except Exception, e:
        log.warning("Failed to perform a spam check with mollom")
        log.exception(e)
        return False, MOLLOM_UNSURE

    log.info("Mollom says: {0}".format(cc))
    return True, cc['spam']