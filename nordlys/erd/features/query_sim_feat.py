"""
Methods for Contextual features (LM-based features)


NOTE: This class does not perform any pre-processing on the mention.
Removal of special characters and encodings should be performed before.

@author: Faegheh Hasibi
"""

from __future__ import division
import re
import math
from nordlys.erd import econfig
from nordlys.retrieval.lucene_tools import Lucene
from nordlys.retrieval.scorer import ScorerLM, ScorerMLM


class QuerySimFeat(object):
    """
    Attributes:
        query: string
    """
    DEBUG = 0

    def __init__(self, query):
        self.query = query

    def lm_score(self, entity_id, field=Lucene.FIELDNAME_CONTENTS):
        """
        LM score between entity field and query (JM smoothing, lambda=0.1).

        :param entity_id: dbpedia uri
        :param field: field name
        :return MLM score
        """
        params = {'field': field}
        score = ScorerLM(econfig.LUCENE, self.query, params).score_doc(entity_id)
        if score is None:
            return None
        return math.exp(score)

    def mlm_score(self, entity_id, weights):
        """
        MLM similarity between the entity and query (JM smoothing, lambda=0.1).

        :param entity_id: dbpedia uri
        :param weights: dictionary {field: weight, ...}
        :return MLM score
        """
        params = {'field_weights': weights}
        score = ScorerMLM(econfig.LUCENE, self.query, params).score_doc(entity_id)
        if score is None:
            return None
        return math.exp(score)

    def nllr_lm_score(self, entity_id, field=Lucene.FIELDNAME_CONTENTS):
        """
        NLLR-LM score between entity field and query (JM smoothing, lambda=0.1).

        :param entity_id: dbpedia uri
        :param field: field name
        :return: score
        """
        if self.DEBUG:
            print entity_id
        weights = {field: 1}
        return self.nllr_mlm_score(entity_id, weights)

    def nllr_mlm_score(self, entity_id, weights):
        """
        NLLR-MLM similarity between the entity and query (JM smoothing, lambda=0.1).

        :param entity_id: dbpedia uri
        :param weights: dictionary {field: weight, ...}
        :return NLLR-MLM score
        """
        if self.DEBUG:
            print entity_id
        lucene_doc_id = econfig.LUCENE.get_lucene_document_id(entity_id)
        p_t_theta_d = {}
        for t in set(self.query.split()):
            p_t_theta_d[t] = ScorerMLM(econfig.LUCENE, self.query, {}).get_mlm_term_prob(lucene_doc_id, weights, t)
        score = self.nllr(self.query, p_t_theta_d, weights)
        if score is None:
            return None
        return math.exp(score)

    @staticmethod
    def nllr(query, term_probs, fields):
        """
        Computed Normalized query likelihood (NLLR):
            NLLR(q,d) = \sum_{t \in q} P(t|q) log P(t|\theta_d) - \sum_{t \in q} p(t|q) log P(t|C)
            where:
                P(t|q) = n(t,q)/|q|
                P(t|C) =  \sum_{f} \mu_f * P(t|C_f)
                P(t|\theta_d) = smoothed LM/MLM score

        :param term_probs: dictionary {t: p_t_tetha_d, ...}
        :param fields: dictionary {field: weight, ...}
        :return: NLLR score
        """
        # none of query terms are in the collection
        if sum(term_probs.values()) == 0:
            if QuerySimFeat.DEBUG:
                print "\t\tP_mlm(q|theta_d) = None"
            return None
        query_len = len(query.split())
        left_sum, right_sum = 0, 0
        for t, p_t_theta_d in term_probs.iteritems():
            if p_t_theta_d == 0:  # Skips the term if it is not in the collection
                continue
            p_t_C = QuerySimFeat.__term_collec_prob(t, fields)
            p_t_q = QuerySimFeat.__query_tf(query, t) / query_len
            left_sum += p_t_q * math.log(p_t_theta_d)
            right_sum += p_t_q * math.log(p_t_C)
            if QuerySimFeat.DEBUG:
                print "\tP(\"" + t + "\"|d) =", p_t_theta_d, "\tP(\"" + t + "\"|C) =", p_t_C, "\tp(\"" + t + "\"|q) =", p_t_q
        nllr_q_d = left_sum - right_sum
        if QuerySimFeat.DEBUG:
            print "\t\tNLLR(" + query + "|theta_d) = " + str(nllr_q_d)
        return nllr_q_d

    @staticmethod
    def __term_collec_prob(term, fields):
        """
        Computes term collection probability for NLLR: P(t|C) =  \sum_{f} \mu_f * P(t|C_f)

        :param term: string
        :param fields:  dictionary {field: weight, ...}
        :return: probability P(t|C)
        """
        p_t_C = 0
        for f, mu_f in fields.iteritems():
            len_C_f = econfig.LUCENE.get_coll_length(f)
            tf_t_C_f = econfig.LUCENE.get_coll_termfreq(term, f)
            p_t_C += mu_f * (tf_t_C_f / len_C_f)
        return p_t_C

    @staticmethod
    def __query_tf(query, term):
        """Gets number of times term appeared in the query."""
        count = 0
        for q_term in query.split():
            if term == q_term:
                count += 1
        return count

    def context_sim(self, entity_id, mention, field=Lucene.FIELDNAME_CONTENTS):
        """
        LM score of entity to the context of query (context means query - mention)
            E.g. given the query "uss yorktown charleston" and mention "uss",
                query context is " yorktown charleston"
        :param entity_id: dbpedia uri
        :param mention: string
        :param field: field name
        :return context similarity score
        """
        # get query context
        match = re.search(mention, self.query)
        if match is None:
            raise Exception("NOTE: Mention \"" + mention + "\" is not found in the query \"" + self.query + "\"")
        mention_scope = match.span()
        q_context = self.query[:mention_scope[0]] + self.query[mention_scope[1]:]
        # scoring
        lucene_doc_id = econfig.LUCENE.get_lucene_document_id(entity_id)
        p_t_theta_d = {}
        for t in set(q_context.strip().split()):
            p_t_theta_d[t] = ScorerMLM(econfig.LUCENE, self.query, {}).get_mlm_term_prob(lucene_doc_id, {field: 1}, t)
        score = self.nllr(q_context.strip(), p_t_theta_d, {field: 1})
        if score is None:
            return 0
        return math.exp(score)
        # context similarity using MLM score
        # score = ScorerLM(econfig.LUCENE, q_context.strip(), {'field': field}).score_doc(entity_id)
        # if score is None:
        #     return 0
        # return math.exp(score)

    def query_set_sim(self, en_ids, weights):
        """ Calculates similarity between query and set.
        sim(q|e1, e2, ..., en) = Mul_i (Sum_j ( p(t_i|e_j) ) ) = Mul_i (Sum_j ( Sum_f (weight_f * p(t_i|theta_e_j_f))))
        """
        # fielded_weights = self.__get_weights(weights)
        scorer = ScorerMLM(econfig.LUCENE, self.query, {})  # {'field_weights': fielded_weights})

        p_t_theta_d = {}
        for t in set(self.query.split()):
            p_t_theta_d[t] = 0
            for en in en_ids:
                lucene_doc_id = scorer.lucene.get_lucene_document_id(en)
                p_t_theta_d[t] += scorer.get_mlm_term_prob(lucene_doc_id, weights, t)
        score = self.nllr(self.query, p_t_theta_d, weights)
        if score is None:
            return 0
        return math.exp(score)


def main():
    # m1 = "the music man"
    # m2 = "uss yorktown charleston sc"
    # m3 = "the Beatles Rock Band"
    # m3 = "hawaii real estate family resale OR foreclosure"
    # m5 = "yahoo! travel"

    en = "<dbpedia:New_York>"
    # en1 = "<dbpedia:The_Beatles:_Rock_Band>"
    en2 = "<dbpedia:Charleston,_South_Carolina>"
    # en3 = "<dbpedia:The_Music_Man_(film)>"
    # en4 = "<dbpedia:Bishopric_of_Utrecht>"
    # en5 = "<dbpedia:University_of_Dayton>"
    # en4 = "<dbpedia:Yahoo!>"
    en5 = "<dbpedia:Kris_Jenner>"

    extractor = QuerySimFeat("jenner divorce rumors")
    print extractor.context_sim(en5, "jenner")
    print extractor.context_sim(en5, "divorce")
    print extractor.lm_score(en5)
    print extractor.mlm_score(en5, {'names': 0.2, 'contents': 0.8})
    print extractor.mlm_score(en5, {'names': 0.4, '<dbo:wikiPageWikiLink>': 0.4, 'contents': 0.2})

    print "*************"
    extractor1 = QuerySimFeat("new york")
    print extractor1.context_sim(en, "new york")
    print extractor1.lm_score(en)

    print "************"
    extractor2 = QuerySimFeat("chamber of commerce charleston sc")
    print extractor2.context_sim(en2, "charleston")
    print extractor2.context_sim(en2, "charleston", econfig.TITLE)

if __name__ == '__main__':
    main()
