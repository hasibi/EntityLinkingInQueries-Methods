"""
Score a single DBpedia entity against a query.

@author: Krisztian Balog
@author: Faegheh Hasibi
"""

from __future__ import division
import argparse
import math
from nordlys.retrieval.lucene_tools import Lucene


class EntityScorer(object):

    def __init__(self, index_dir, use_lm=False):
        self.lucene = Lucene(index_dir)
        self.lucene.open_searcher()
        self.use_lm = use_lm
        if use_lm:
            self.lucene.set_lm_similarity_jm()

    def get_term_probs(self, terms, lucene_entity_id, field, smoothing_param=0.1):
        """ Returns probability of each term using JM smoothing
        i.e. for each term: p(t|theta_e_f) = [(1-lambda) n(t, e_f)/|e_f|] + [lambda n(t, C_f)/|C_f|]

        :param terms: list of terms in the query
        :param entity_uri: entity URI, e.g., <dbpedia:American_Civil_War>
        :param field: entity field name, e.g. <dbo:abstract>
        :param smoothing_param: parameter used for JM smoothing
        :return: dictionary of terms with their probabilities
        """
        en_term_freqs = self.lucene.get_doc_termfreqs(lucene_entity_id, field)
        len_e_f = sum(en_term_freqs.values())
        len_C_f = self.lucene.get_coll_length(field)
        term_prob_dict = {}
        for t in terms:
            # p(t|theta_e_f) = [(1-lambda) n(t, e_f)/|e_f|] + [lambda n(t, C_f)/|C_f|]
            en_term_freq = en_term_freqs.get(t, 0)
            p_t_e_f = en_term_freq / len_e_f
            coll_term_freq = self.lucene.get_coll_termfreq(t, field)
            p_t_C_f = coll_term_freq / len_C_f
            p_t_theta_e_f = ((1-smoothing_param) * p_t_e_f) + (smoothing_param * p_t_C_f)
            term_prob_dict[t] = p_t_theta_e_f
        return term_prob_dict

    def score_lm(self, query, entity_uri, field=Lucene.FIELDNAME_CONTENTS):
        """ LM score for the given query and entity field. """
        lucene_entity_id = self.lucene.get_lucene_document_id(entity_uri)

        terms = query.split()
        term_probs = self.get_term_probs(set(terms), lucene_entity_id, field)
        p_q_theta_e = 0  # p(q|theta_e) = prod(p(t|theta_e)) ; we return log(p(q|theta_e))
        for t in terms:
            p_t_theta_e = term_probs[t]
            p_q_theta_e += math.log(1 + p_t_theta_e)
        return p_q_theta_e

    def score_mlm(self, query, entity_uri, weights):
        """ Scores a given entity using the Mixture of Language Models (using JM smoothing)

        :param query: query string
        :param entity_uri: (prefixed) entity URI, e.g., <dbpedia:American_Civil_War>
        :param weights: dictionary with field names as keys and weights as values. Weights should add up to 1.
        :return:
        """
        lucene_entity_id = self.lucene.get_lucene_document_id(entity_uri)

        # Gets all term_probabilities and store them in a dictionary
        terms = query.split()
        field_term_probs = {}
        for field in weights.keys():
            field_term_probs[field] = self.get_term_probs(set(terms), lucene_entity_id, field)

        # p(q|theta_e) = prod(p(t|theta_e)) ; we return log(p(q|theta_e))
        p_q_theta_e = 0
        for t in terms:
            # p(t|theta_e) = sum(mu_f * p(t|theta_e_f))
            p_t_theta_e = 0
            for f, mu_f in weights.iteritems():
                p_t_theta_e_f = field_term_probs[f][t]
                p_t_theta_e += mu_f * p_t_theta_e_f
            p_q_theta_e += math.log(1 + p_t_theta_e)
        return p_q_theta_e

    def score_mlm_tc(self, query, entity_uri):
        weights = {"<rdfs:label>": 0.2, Lucene.FIELDNAME_CONTENTS: 0.8}
        return self.score_mlm(query, entity_uri, weights)

    def score_mlm_tlc(self, query, entity_uri):
        weights = {"<rdfs:label>": 0.4, "<dbo:wikiPageWikiLink>": 0.4,  Lucene.FIELDNAME_CONTENTS: 0.2}
        return self.score_mlm(query, entity_uri, weights)

    def score_mlm_old(self, query, entity_uri, weights):
        """
        Scores a given entity using the Mixture of Language Models.

        Args:
            query: query string
            entity_uri: (prefixed) entity URI, e.g., <dbpedia:American_Civil_War>
            weights: dictionary with field names as keys and weights as values. Weights should add up to 1.
        Return:

        """
        if not self.use_lm:
            raise Exception("EntityScorer must be created with use_lm=True")

        # query for the ID field
        id_query = self.lucene.get_id_lookup_query(entity_uri)

        # this is an ugly (and slow) solution:
        # we score each query term against each field
        terms = query.split(" ")
        p_q = 0
        for term in terms:
            p_t = 0
            #print "scoring term '" + term + "'"
            for field in weights.keys():
                term_query = self.lucene.get_lucene_query(term, field)

                # create Boolean query (term_query AND id_query)
                and_query = self.lucene.get_and_query([term_query, id_query])

                # we only need the top document (and there should only be one)
                topdoc = self.lucene.searcher.search(and_query, 1).scoreDocs

                # we assume that what we get back is \propto log P(t|\theta_{e_f})
                """
                @todo what we actually get back is not this!
                1) We get 0 back if the field doesn't contain the term. Instead, we should be getting back the the
                background probability (times the smoothing param)
                2) Additional transformation steps are likely applied in Lucene. This needs to be checked.
                """
                p_t_f = 0 if len(topdoc) == 0 else math.exp(topdoc[0].score)
                #print "\tP(" + term + "|" + field + " )= " + str(p_t_f)

                #
                p_t = weights[field] * p_t_f

            #print "\tP(" + term + "|e)= " + str(p_t)
            # P(q|\theta_e) = \prod_{t \in q} P(t|\theta_q)^{n(t,q)}
            # => log P(q|\theta_e) = \sum_{t \in q} n(t,q) * log P(t|\theta_q)
            """
            @todo we add 1 here because p_t might be 0. Normally, it would aways be > 0 because of the background model
            """
            p_q += math.log(1 + p_t)

        return p_q

    def score_lm_old(self, query, entity, field=Lucene.FIELDNAME_CONTENTS):
        """Entity is matched against the ID field in the index.

        The score is zero if either the entity ID is invalid or it does
        not contain any of the query term.
        """

        # "normal" query
        normal_query = self.lucene.get_lucene_query(query, field)
        # query for the ID field
        id_query = self.lucene.get_id_lookup_query(entity)
        # create Boolean query (normal_query AND id_query)
        and_query = self.lucene.get_and_query([normal_query, id_query])

        # we only need the top document (and there should only be one)
        topdoc = self.lucene.searcher.search(and_query, 1).scoreDocs

        if len(topdoc) == 0:
            return 0

        return topdoc[0].score
            

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--index", help="index directory", type=str)
    parser.add_argument("-q", "--query", help="lookup a document id", type=str)
    parser.add_argument("-e", "--entity", help="term vector for a document id", type=str)
    parser.add_argument("-lm", help="Language Model(LM) score, specify the fields", type=str)
    parser.add_argument("-mlm", help="Mixture of Language Model(MLM) score", choices=['tlc', 'tc'])
    args = parser.parse_args()

    if (args.index is None) or (args.query is None) or (args.entity is None):
        raise Exception("Err: Specify index directory, query, and entity ID")

    # index_dir = "/hdfs1/krisztib/dbpedia-3.9-indices/index2/"
    index_dir = args.index
    print "Index:       " + index_dir + "\n"
    es = EntityScorer(index_dir, True)

    # query = "battles in the civil war"
    # entity = "<dbpedia:American_Civil_War>"

    # LM score for fields e.g. "catchall": all fields, "<rdfs:label>": title, "<rdfs:comment>": abstract
    if args.lm:
        field = args.lm
        print "Query:" + args.query + "\nEntity:" + args.entity + "\nField: " + field
        if field == "catchall":
            print "LM score: ", es.score_lm(args.query, args.entity)
            print "Old LM score: ", es.score_lm_old(args.query, args.entity)
        else:
            print "LM score: ", es.score_lm(args.query, args.entity, field)
            print "Old LM score: ", es.score_lm_old(args.query, args.entity, field)
    # MLM score
    elif args.mlm:
        print "Query:" + args.query + "\nEntity:" + args.entity
        if args.mlm == "tc":
            print "MLM-tc score: ", es.score_mlm_tc(args.query, args.entity)
            weights = {"<rdfs:label>": 0.2, Lucene.FIELDNAME_CONTENTS: 0.8}
            print "Old MLM score: ", es.score_mlm_old(args.query, args.entity, weights)
        elif args.mlm == "tlc":
            print "MLM-tlc score: ", es.score_mlm_tlc(args.query, args.entity)
            weights = {"<rdfs:label>": 0.4, "<dbo:wikiPageWikiLink>": 0.4,  Lucene.FIELDNAME_CONTENTS: 0.2}
            print "Old MLM score: \t", es.score_mlm_old(args.query, args.entity, weights)
        
if __name__ == '__main__':
    main()
