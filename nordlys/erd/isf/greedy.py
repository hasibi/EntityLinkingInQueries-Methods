"""
Generative model for interpretation set finding

@author: Faegheh Hasibi
"""

from __future__ import division
from nordlys.erd.ml.cer_instances import CERInstances
from nordlys.erd.ml.isf_instances import ISFInstances, ISFInstance
from nordlys.erd.query.segmentation import is_overlapping

rel_range = []


class Greedy(object):
    DEBUG = 1

    def __init__(self, score_th,  get_rel=True):
        self.score_th = score_th
        self.get_rel = get_rel

    def gen_isf_inss(self, cer_inss):
        """
        Generates top interpretation set for each query.

        :param cer_inss: erd.ml.cer_instances
        :return: erd.ml.isf_instances
        """
        isf_inss = ISFInstances()
        isf_ins_id = 0
        inss_dict = cer_inss.group_by_query()
        for qid, inss_list in inss_dict.iteritems():
            pruned_inss = self.prune_by_score(CERInstances(inss_list))
            pruned_inss = self.prune_containment_mentions(pruned_inss)
            interpretations = self.create_interpretations(pruned_inss)
            for inter in interpretations:
                if len(inter) == 0:
                    continue
                # converts group of cer instances to an ISF instance
                isf_ins_score = sum([ins.score for ins in inter]) / len(inter)
                isf_ins = ISFInstance.cer_to_isf(CERInstances(inter), isf_ins_score, isf_ins_id=isf_ins_id)
                if isf_ins is not None:
                    isf_ins.target = "1"
                    isf_inss.add_instance(isf_ins)
                    isf_ins_id += 1
        return isf_inss

    @staticmethod
    def create_interpretations(query_inss):
        """
        Groups CER instances as interpretation sets.

        :return list of lists, where each list represents an interpretation [[ins, ...], ...]
        """
        interpretations = [dict()]  # list of dictionaries {men: ins}
        for ins in query_inss.get_all():
            added = False
            for inter in interpretations:
                mentions = inter.keys()
                mentions.append(ins.mention)
                if not is_overlapping(mentions):
                    inter[ins.mention] = ins
                    added = True
            if not added:
                interpretations.append({ins.mention: ins})
        return [inter.values() for inter in interpretations]

    def prune_by_score(self, query_inss):
        """ prunes based on a static threshold of ranking score."""
        valid_inss = []
        for ins in query_inss.get_all():
            if ins.score >= self.score_th:
                valid_inss.append(ins)
        return CERInstances(valid_inss)

    def prune_containment_mentions(self, query_inss):
        """Deletes containment mentions, if they have lower score."""
        if len(query_inss.get_all()) == 0:
            return query_inss

        valid_inss = dict()  # {en_id: ins}
        valid_mens = set()
        # if self.is_ambiguous_query(query_inss):
        #     for ins in query_inss.get_all():
        #         valid_inss[ins.en_id] = ins
        #     print CERInstances(valid_inss.values()) .to_str(), "********"
        #
        # else:
        for ins in sorted(query_inss.get_all(), key=lambda item: item.score, reverse=True):
            is_contained = False
            for men in valid_mens:
                if (ins.mention in men) or (men in ins.mention):
                    is_contained = True
            if not is_contained:
                valid_inss[ins.mention] = ins
                valid_mens.add(ins.mention)
        return CERInstances(valid_inss.values())

    def is_ambiguous_query(self, query_inss):
        """Checks if the query is ambiguous or not.
        Ambiguous queries contain single mention that xan refer to multiple entities
        """
        sorted_inss = sorted(query_inss.get_all(), key=lambda item:len(item.mention.split()), reverse=True)
        longest_mention = sorted_inss[0].mention
        print longest_mention
        is_ambiguous = True if sorted_inss[0].q_content == longest_mention else False
        for ins in sorted_inss:
            if ins.mention not in longest_mention:
                is_ambiguous = False
        return is_ambiguous


def main(args):
    cer_inss = CERInstances.from_json(args.input)
    file_name = args.input[:args.input.rfind(".json")] + "-greedy-" + str(args.threshold)
    greedy_isf = Greedy(args.threshold)
    isf_inss = greedy_isf.gen_isf_inss(cer_inss)
    isf_inss.to_erdeval(file_name + ".erdeval")
    isf_inss.to_json(file_name + ".json")


if __name__ == "__main__":
    main()