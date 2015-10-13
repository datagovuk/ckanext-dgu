
import sys
import logging

import requests

from ckan.lib.cli import CkanCommand
import ckan.plugins as p
# No other CKAN imports allowed until _load_config is run,
# or logging is disabled

VOCABS = ['la_service']

class VocabsCmd(CkanCommand):
    '''
    Management of vocabularies stored in CKAN. e.g. LGA services

    paster vocabs [list]   - list the vocabs in CKAN
    paster vocabs sync <vocab>  - sync the named vocabs (defaults to all of them)
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = None
    min_args = 0

    def __init__(self, name):
        super(VocabsCmd, self).__init__(name)

    def command(self):
        self._load_config()
        log = logging.getLogger(__name__)

        if not self.args or self.args[0] == 'list':
            self.list()
            sys.exit(0)
        cmd = self.args[0]
        if cmd == 'sync':
            self.sync(self.args[1:])
        else:
            raise NotImplementedError(cmd)

    def list(self):
        ckan_vocabs = [vocab['name'] for vocab in self._get_ckan_vocabs()]
        print '%d/%d vocabularies loaded in ckan' % (len(ckan_vocabs), len(VOCABS))
        from pprint import pprint
        for vocab in VOCABS:
            if vocab in ckan_vocabs:
                print '%s (in ckan):' % vocab
                pprint(ckan_vocabs[vocab])
            else:
                print '%s (not in ckan)' % vocab

    def _get_ckan_vocabs(self):
        from ckan import model
        context = {'model': model, 'session': model.Session,
                   'ignore_auth': True}
        return p.toolkit.get_action('vocabulary_list')(context, {})

    def sync(self, vocab_names):
        from ckan import model
        if not vocab_names:
            vocab_names = VOCABS
        for vocab_name in vocab_names:
            if vocab_name == 'la_service':
                # Get all the services in CSV (UTF8), as described at:
                # http://standards.esd.org.uk/?uri=list%2Fservices&tab=downloads
                import csv
                from io import BytesIO
                url = 'http://standards.esd.org.uk/csv?uri=list/services'
                print 'Requesting services: %s' % url
                res = requests.get(url)
                # e.g.
                # Identifier,Label,Description,Created,Modified,History notes,Type,
                # 1614,16 to 19 bursary fund,"Those aged between 16 and 19 years who think they might struggle with the costs for full-time education or training, may be eligible for a bursary.",2013-04-03,2013-04-03,Added in version 4.00.,Service,
                tags = []
                # res.text is the UTF8 encoded content, as csv can't handle unicode
                for service_dict in csv.DictReader(BytesIO(res.content)):
                    # convert utf8 to unicode
                    for key in service_dict:
                        service_dict[key] = unicode(service_dict[key], "utf-8")
                    uri = 'http://id.esd.org.uk/service/%s' % service_dict['Identifier']
                    tag = {'name': uri,
                            'vocabulary_id': vocab_name}
                    tags.append(tag)
                context = {'model': model, 'session': model.Session,
                        'ignore_auth': True}
                data = {'name': vocab_name,
                        'tags': tags}
                res = p.toolkit.get_action('vocabulary_create')(context, data)
                assert res['success'], res
            else:
                raise NotImplementedError(vocab_name)


