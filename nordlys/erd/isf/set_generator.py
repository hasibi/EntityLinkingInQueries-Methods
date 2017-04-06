"""
Generates candidate sets and their features.

@author: Faegheh Hasibi
"""
from __future__ import division

from collections import defaultdict
import numpy

from nordlys.erd.ml.isf_instances import ISFInstance, ISFInstances
from nordlys.erd.ml.cer_instances import CERInstances
from nordlys.erd.query.query import Query
from nordlys.erd.query.segmentation import gen_iset


class SetGen(object):
    """
    Attributes:
        cer_inss: CERInstances from the CER step.
        k: the threshold for top_k instances.
        is_ltr: True if CER instances are ranked using LTR.
    """

    def __init__(self, cer_inss, k=None):
        self.cer_inss = cer_inss
        self.k = k
        self.is_ltr = self.__is_ltr(cer_inss)

    @staticmethod
    def __is_ltr(cer_inss):
        """Checks if CER instances are ranked using LTR or MLM."""
        is_ltr = False
        for cer_ins in cer_inss.get_all():
            if len(cer_ins.features) > 0:
                is_ltr = True
                break
        return is_ltr

    def normalize_mlm(self):
        """Normalizes MLM scores for each query using Min-Max normalization."""
        if self.is_ltr:
            return

        print "   - MLM score normalization ..."
        query_inss_dict = self.cer_inss.group_by_query()
        for qid, inss_list in query_inss_dict.iteritems():
            mlm_scores = [ins.score for ins in inss_list]
            # avg_q_score, std_q_score = numpy.average(mlm_scores), numpy.std(mlm_scores)
            min_q_score, max_q_score = min(mlm_scores), max(mlm_scores)
            for ins in inss_list:
                # normalized_mlm = (ins.score - avg_q_score) / std_q_score
                if min_q_score == max_q_score:
                    normalized_mlm = 0.5
                else:
                    normalized_mlm = (ins.score - min_q_score) / float(max_q_score - min_q_score)
                self.cer_inss.get_instance(ins.id).score = normalized_mlm

    def filter_by_k(self):
        """
        Filters top-k entities for each query.
        Return all instances, if k is None.
        """
        self.cer_inss.sort()

        if self.k is None:
            return self.cer_inss
        filtered_inss = CERInstances()

        for ins in self.cer_inss.get_all():
            if ins.rank <= self.k:
                filtered_inss.add_instance(ins)
        return filtered_inss

    def gen_isf_inss(self):
        """
        Generates ISF instances.
            - For each query creates all interpretation sets.
            - Convert each interpretation set to an ISF instance.
            - Each ISF instance consists of an "interpretation_set" and its "query".
            - Transfer some CER attributes to the ISF instances

        :return erd.ml.ISFInstances
        """
        print "Generating ISF instances from CER instances..."

        self.normalize_mlm()

        print "   - Filtering top-k entities ..."
        self.cer_inss = self.filter_by_k()

        print "   - Converting CER instances to ISF instances ..."
        query_inss_dict = self.cer_inss.group_by_query()
        isf_inss = ISFInstances()
        ins_id = 0
        for q_id, inss_list in query_inss_dict.iteritems():
            # Generates interpretation sets of each query
            q_content = inss_list[0].q_content
            # here we filter instances with score=None
            mention_en_dict = self.__get_mention_en_dict(q_id, query_inss_dict)
            query = Query(q_id, q_content)
            iset_query = gen_iset(query, mention_en_dict)
            for iset in iset_query:
                isf_ins = ISFInstance(ins_id)
                isf_ins.inter_set = iset
                isf_ins.q_id = q_id
                isf_ins.q_content = q_content
                isf_inss.add_instance(isf_ins)
                ins_id += 1
                if ins_id % 10000 == 0:
                    print "   \tConverting is done until instance", ins_id
        # Adds CER attributes to the instances.
        print "   - Transferring CER attributes to ISF instances ..."
        self.add_cer_atts(isf_inss)
        return isf_inss

    def add_cer_atts(self, isf_inss):
        """
        Adds CER scores to the ISF instances.
        CER scores are stored in dictionaries with entity-score pairs.

        :param cer_inss: CER instances
        :param isf_inss: ISF instances
        """
        count = 0
        query_inss_dict = self.cer_inss.group_by_query()
        for isf_ins in isf_inss.get_all():

            # Stores cer instances based on entity and mention {(entity, mention):ins, ...}
            en_men_ins = {}
            for cer_ins in query_inss_dict[isf_ins.q_id]:
                en_men_ins[(cer_ins.en_id, cer_ins.mention)] = cer_ins
            # Generates a dictionary for CER attributes {en_id: {score: xxx, rank: xxx, commonness:xxx}, ...}
            cer_atts = {}
            for en_id, mention in isf_ins.inter_set.iteritems():
                cer_atts[en_id] = {}
                cer_atts[en_id]['score'] = en_men_ins[(en_id, mention)].score
                cer_atts[en_id]['rank'] = en_men_ins[(en_id, mention)].rank
                cer_atts[en_id]['commonness'] = en_men_ins[(en_id, mention)].commonness
                cer_atts[en_id]['fb_id'] = en_men_ins[(en_id, mention)].freebase_id
                # Adds MLM-tc score to the instances ranked using LTR method
                if self.is_ltr:
                    cer_atts[en_id]['mlm-tc'] = en_men_ins[(en_id, mention)].features['mlm-tc']

            isf_ins.cer_atts = cer_atts

            count += 1
            if count % 10000 == 0:
                print "   \tTransferring is done until instance " + str(isf_ins.id)

    @staticmethod
    def __get_mention_en_dict(q_id, query_inss_dict):
        """
        Generates a dictionary of mentions mapped to a list of entity_ids for the given query.

        :param q_id: String, query id
        :return dictionary {mention: [en_id, ...], ...}
        """
        q_inss_list = query_inss_dict[q_id]
        mention_en_dict = defaultdict(set)
        for ins in q_inss_list:
            if ins.score is None:
                print "_________________________"
                print "NONE score instance ignored: ", ins.q_id, ins.en_id, ins.score
                print "_________________________"
                continue
            mention_en_dict[ins.mention].add(ins.en_id)
        return mention_en_dict


def main(args):
    """
    Required args: -gs -k <int> -in <CER_inss_file>
    """
    cer_inss = CERInstances.from_json(args.input)
    generator = SetGen(cer_inss, args.k)
    isf_inss = generator.gen_isf_inss()
    # SetGen.add_cer_atts(isf_inss, cer_inss)
    # Writes ISF instances
    file_name = args.input[:args.input.rfind(".json")] + "-setgen-k" + str(args.k)
    isf_inss.to_json(file_name + ".json")
    # isf_inss.to_str(file_name + ".txt")


        # top_k_ens = SetGen.get_top_k_ens(cer_inss, k)
        # for ins in cer_inss.get_all():
        #     if ins.en_id in top_k_ens[ins.q_id]:
        #         filtered_inss.add(ins)
        # return filtered_inss

    # def get_top_k_ens(self):
    #     """ Generates top-k entities for each query
    #
    #     :return: dict {qid:set(en1, ...), ..}
    #     """
    #     score_dict = dict()  # {qid:{enid: max_score, ...}, ...}
    #     for ins in self.cer_inss.get_all():
    #         if ins.q_id not in score_dict:
    #             score_dict[ins.q_id] = dict()
    #         if (ins.en_id not in score_dict[ins.q_id]) or (score_dict[ins.q_id][ins.en_id] < ins.score):
    #             score_dict[ins.q_id][ins.en_id] = ins.score
    #
    #     # Keeps entities that are among top-k
    #     filtered_ens = defaultdict(list)
    #     for qid, ens_score in score_dict.iteritems():
    #         sorted_ens = sorted(ens_score.items(), key=lambda tup: tup[1], reverse=True)
    #         filtered_ens[qid] = list()
    #         for i, (en, score) in enumerate(sorted_ens):
    #             if i >= self.k:
    #                 break
    #             filtered_ens[qid].append(en)
    #     return filtered_ens