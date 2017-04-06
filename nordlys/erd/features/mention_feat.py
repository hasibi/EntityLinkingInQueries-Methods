"""
Methods for extracting mention features.

NOTE: This class does not perform any pre-processing on the mention.
Removal of special characters and encodings should be performed before.

@author: Faegheh Hasibi
"""

import sys

from nordlys.erd import econfig
from nordlys.erd.query.query import Query, Mention


class MentionFeat(object):
    """
    Attributes:
        Mention: nordlys.erd.query.Mention

    - For all features, the mention is converted to lower case and the stop chars are removed.
    """
    def __init__(self, mention, sf_source):
        self.mention = Mention(mention, sf_source)

    def mention_len(self):
        """ number of terms in the mention"""
        return len(self.mention.text.split())

    def matches(self, cmn_th=None):
        """
        Number of entities whose surface form equals the mention.
        Uses both DBpedia and Freebase name variants
        """
        all_matches = self.mention.get_men_candidate_ens(cmn_th, filter=False)
        return len(all_matches)

    def ntem(self):
        """ Number of entities whose title equals the mention """
        target_ens = []
        for source, en_ids in self.mention.matched_ens.iteritems():
            if source == econfig.TITLE:
                target_ens = en_ids.keys()
        return len(target_ens)

    def smil(self):
        """ Number of entities whose title equals a sub-n-gram of the mention"""

        # Considers the mention as a query and finds its n-grams
        men_query = Query("_", self.mention.text)
        ngrams = men_query.get_ngrams()
        # Check whether the entity title is equal to n-gram
        target_ens = []
        for ngram in ngrams:
            for source, en_ids in Mention(ngram, self.mention.sf_source).matched_ens.iteritems():
                if source == econfig.TITLE:
                    target_ens += en_ids.keys()
        return len(target_ens)

    def len_ratio(self, query):
        """ 
        Len ratio is: len(mention) / len(query)
            - len is number of terms of a string

        :param query: string
        """
        val = float(len(self.mention.text.split())) / len(Query.preprocess(query).split())
        return val


def main(argv):
    # q1 = "the music man"
    q2 = "uss yorktown charleston sc"
    # q3 = "the Beatles Rock Band"
    # q4 = "hawaii real estate family resale OR foreclosure"
    # q5 = "yahoo! travel"

    extractor = MentionFeat(argv[0])  # e.g. yahoo!, Carolina, charleston sc

    print extractor.mention_len()
    print extractor.matches(0.01)
    print extractor.ntem()
    print extractor.smil()
    print extractor.len_ratio(q2)

if __name__ == '__main__':
    main(sys.argv[1:])
