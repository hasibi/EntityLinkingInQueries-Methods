"""
Features related to FACC index.
"""

from __future__ import division
import math


class FACCFeat(object):
    def __init__(self, facc_lucene):
        self.facc_lucene = facc_lucene
        self.and_freq = {}
        self.facc_lucene.open_searcher()

    def __get_and_freq(self, fb_ids):
        """
        returns "and" occurrences of entities in the corpus.

        :param fb_ids: list of freebase ids
        """
        fb_ids = tuple(sorted(set(fb_ids)))
        if fb_ids in self.and_freq:
            return self.and_freq[fb_ids]

        term_queries = []
        for fb_id in fb_ids:
            term_queries.append(self.facc_lucene.get_id_lookup_query(fb_id, "content"))
        and_query = self.facc_lucene.get_and_query(term_queries)
        self.and_freq[fb_ids] = self.facc_lucene.searcher.search(and_query, 1).totalHits
        return self.and_freq[fb_ids]

    def __get_or_freq(self, fb_ids):
        """
        returns "or" occurrences of entities in the corpus.

        :param fb_ids: list of freebase ids
        """
        term_queries = []
        for fb_id in fb_ids:
            term_queries.append(self.facc_lucene.get_id_lookup_query(fb_id, "content"))
        or_query = self.facc_lucene.get_or_query(term_queries)
        return self.facc_lucene.searcher.search(or_query, 1).totalHits

    def joint_prob(self, fb_ids):
        """
        # prob = doc(id_1, ..id_n) / #total docs

        :param fb_ids: list of freebase ids
        """
        num_docs = self.facc_lucene.num_docs()
        return self.__get_and_freq(fb_ids) / num_docs

    def entropy(self, fb_ids):
        """
        H(a) = -P(a)log(P(a))-(1-P(a))log(1-p(a))

        :param fb_ids: list of freebase ids
        """
        p_a = self.joint_prob(fb_ids)
        if p_a == 0:
            return 0
        return -(p_a * math.log(p_a)) - ((1 - p_a) * math.log((1 - p_a)))

    def jc(self, fb_ids):
        """
        Jaccard similarity w.r.t the co-occurrences of entities in FACC:
            #docs both entities co-occur / #docs at least one entity occurs

        :param fb_ids: list of freebase ids (at least two fb-ids are required)
        """
        if len(fb_ids) == 1:
            return -1
        and_freq = self.__get_and_freq(fb_ids)
        if and_freq == 0:
            return 0
        return and_freq / self.__get_or_freq(fb_ids)

    def mw_rel(self, fb_ids):
        """
        MV(ids) = 1- (log(max(ids)) - log(\cap_ids)) / (log(all_docs) - log(min(ids))

        :param fb_ids: list of freebase ids (at least two fb-ids are required)
        """
        # # @todo: Update this function based on DEXTER implementation
        # en_freqs = [self.__get_and_freq([fb_id]) for fb_id in fb_ids]
        # if max(en_freqs) == 0:
        #     return 0
        # conj = self.__get_and_freq(fb_ids)
        # if conj == 0:
        #     numerator = math.log(max(en_freqs))
        # else:
        #     numerator = math.log(max(en_freqs)) - math.log(self.__get_and_freq(fb_ids))
        # if min(en_freqs) == 0:
        #     denominator = math.log(self.facc_lucene.num_docs())
        # else:
        #     denominator = math.log(self.facc_lucene.num_docs()) - math.log(min(en_freqs))
        # return 1 - numerator / denominator

        if len(fb_ids) == 1:  # to speed-up
            return -1
        en_freqs = [self.__get_and_freq([fb_id]) for fb_id in fb_ids]
        if min(en_freqs) == 0:
            return 0
        conj = self.__get_and_freq(fb_ids)
        if conj == 0:
            return 0

        numerator = math.log(max(en_freqs)) - math.log(conj)
        denominator = math.log(self.facc_lucene.num_docs()) - math.log(min(en_freqs))
        rel = 1 - (numerator / denominator)
        if rel < 0:
            return 0
        return rel
