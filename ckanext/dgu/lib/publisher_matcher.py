'''Routines for matching publisher names, expressed in different ways.'''

import re
log = __import__('logging').getLogger(__name__)

class PublisherMatcher:
    external_publishers = {} # canonical_name:external_id

    # simplify phrases that can be expressed in
    # multiple ways
    canonical_replacements = [
        ('united kingdom', 'uk'),
        ('primary care trust pct', 'pct'),
        ('primary care trust', 'pct'),
        ('care trust', 'pct'),
        ('nhs pct', 'pct'),
        ('teaching pct', 'pct'),
        ('royal borough', 'council'),
        ('london borough', 'council'),
        ('city council', 'council'), # only durham has county and city council, so not to worry
        ('county council', 'council'),
        ('metropolitan borough council', 'council'),
        ('borough council', 'council'),
        ('northern ireland', ''), # only clash is dfe AND deni
        ('hospitals', 'hospital'),
        ]
    move_words_to_the_end = ['borough', 'pct', 'council', 'department']
    @classmethod
    def canonical_name(cls, name):
        name = name.lower()
        name = re.sub(r'[^a-zA-Z0-9 ]', '', name)
        stop_words = ['and', 'of', 'it', 'the', 'for', '-', 'limited', 'ltd']
        name = ' '.join(w for w in name.split() if not w in stop_words)
        for from_, to in cls.canonical_replacements:
            if from_ in name:
                name = name.replace(from_, to)
        for word in cls.move_words_to_the_end:
            if word in name.split():
                words = name.split()
                words.append(words.pop(words.index(word)))
                name = ' '.join(words)
        return name

    def add_external_publisher(self, external_id, *external_names):
        for name in external_names:
            if not name.strip():
                continue
            canonical_name = self.canonical_name(name)
            if canonical_name in self.external_publishers and \
                   self.external_publishers[canonical_name] != external_id:
                log.warning('Duplicate canonical name: %s (%s AND %s)',
                            canonical_name, external_id,
                            self.external_publishers[canonical_name])
                continue
            self.external_publishers[canonical_name] = external_id

    def match_to_external_publisher(self, name):
        canonical_name = self.canonical_name(name)
        return self.external_publishers.get(canonical_name)
