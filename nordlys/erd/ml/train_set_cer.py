"""
Generates train set for Candidate Entity Finding (CER).
Functionality:
 - Generates train set instances (both normal and random distribution)
 - Add features to the train set instances
 - Calculates statistics of train set

@author: Faegheh Hasibi
"""
from collections import defaultdict

from nordlys.erd import econfig
from nordlys.erd.cer.ranker_ltr import RankerLTR
from nordlys.erd.ml.cer_instances import CERInstances
from nordlys.erd.query.query import Query
from nordlys.erd.groundtruth import erd_gt, ysqle_erd_gt, ysqle_gt
from nordlys.erd.features.entity_mention_feat import EntityMentionFeat


class TrainSetCER(object):
    def __init__(self, commonness_th, sf_source):
        self.commonness_th = commonness_th
        self.sf_source = sf_source
        # self.filter = filter

    def gen_train_set(self, gt_inss, queries, rand=False, ratio=1):
        """
        Generates CER train set for the given queries.
        - The train set is union of ground-truth instances and other candidate instances.
        - Generated instances are without features.

        Args:
            instances: ground-truth instances
            query_dict: {q_id: q_content}, Dictionary of queries.
            rand:
                - False if natural distribution should be used.
                - True, if a set of random instances should eb used
            ratio: ratio of irrelevant to relevant instances for random instances.
                e.g. for 50-50 percentage, ratio is 1.

        Returns:
            erd.ml.CERIns, train set instances
        """
        print "Generating CER train set ..."
        gt_inss_by_query = gt_inss.group_by_query()
        train_inss = CERInstances()
        ins_count = 0
        # for q_id, inss_list in gt_inss_by_query.iteritems():
        for q_id, q_content in queries.iteritems():
            query = Query(q_id, q_content)
            # gets instances for each query
            if rand:
                q_ins_list = self.__get_query_rand_inss(query, gt_inss_by_query[q_id], ratio)
            else:
                q_ins_list = self.__get_query_inss(query, gt_inss_by_query[q_id])
            # append query instances to the train set
            for ins in q_ins_list:
                ins.id = ins_count
                if ins.commonness is None:
                    ins.commonness = EntityMentionFeat(ins.en_id, ins.mention).commonness(self.sf_source)
                train_inss.add_instance(ins)
                ins_count += 1
        print "\nTrain set instances are generated!"
        print "\t#Instances: " + str(len(train_inss.get_all()))
        return train_inss

    def __get_query_inss(self, query, gt_inss):
        """
        Generates instances for a given query.
        The instances are union of ground-truth instances and candidate entities for a given query.

        Args:
            query: query.text
            q_gt_inss : ground-truth instances for a given query.

        Returns:
            List of all instances for the given query.
        """
        all_query_inss = []
        cand_inss = CERInstances.gen_instances(query, self.commonness_th, sf_source=self.sf_source, filter=True)
        for cand_ins in cand_inss.get_all():
            # Checks if the candidate instance is in gt.
            is_gt_ins = False
            for gt_ins in gt_inss:
                if gt_ins.en_id == cand_ins.en_id:
                    is_gt_ins = True
                    break
            if not is_gt_ins:
                all_query_inss.append(cand_ins)
        return all_query_inss + gt_inss

    def gen_cv_set(self, gt_inss, queries):
        """
        Generates sets of entities for cross validation.
        - This set contains entities generated from "entity generation" step(extra entities from ground truth are not added).
        - The label of instances are checked with groundtruth instances.

        Note: We do not use train set for cross validation. Since train set has all positive entities, which affects recall value.
        """
        print "Generating CER cross-validation set ..."
        # generate set of positive entities for each query
        gt_query_en_dict = defaultdict(set)
        for ins in gt_inss.get_all():
            if ins.target == "1":
                gt_query_en_dict[ins.q_id].add(ins.en_id)

        inss_list = []
        for q_id, q_content in queries.iteritems():
            query = Query(q_id, q_content)
            q_inss = CERInstances.gen_instances(query, self.commonness_th, sf_source=self.sf_source, filter=True)
            RankerLTR.add_features(q_inss, self.commonness_th, self.sf_source)
            inss_list.append(q_inss)
        inss = CERInstances.concatenate_inss(inss_list)

        # change target of instances for instances in the groundtruth
        for ins in inss.get_all():
            if ins.en_id in gt_query_en_dict[ins.q_id]:
                ins.target = 1
        return inss

    # # TODO: Test the function again.
    # def __get_query_rand_inss(self, query, gt_inss, ratio):
    #     """
    #     Generates n-random instances for a given query
    #
    #     Args:
    #         query: query.text
    #         gt_inss : Groundtruth instances for a given query
    #         ratio: ratio of irrelevant to relevant instances.
    #             e.g. for 50-50 percentage, ratio is 1
    #
    #     Returns: a list of instances
    #     """
    #     irel_inss = []
    #     all_inss = CERInstances.gen_instances(query, self.commonness_th)
    #     rand_list = [i for i in range(len(all_inss.get_all()))]
    #     shuffle(rand_list)
    #
    #     # generates list of relevant instances
    #     rel_inss = []
    #     for ins in gt_inss:
    #         if ins.target == "1":
    #             rel_inss.append(ins)
    #
    #     for i in xrange(0, len(rand_list)):
    #         if len(irel_inss) == (ratio * len(rel_inss)):
    #             break
    #         ins = all_inss.get_instance(rand_list[i])
    #         # check if the instance is relevant
    #         is_rel_ins = False
    #         for rel_ins in rel_inss:
    #             if rel_ins.en_id == ins.en_id:
    #                 is_rel_ins = True
    #                 break
    #         # adds the instance to list if it is not relevant.
    #         if not is_rel_ins:
    #             irel_inss.append(ins)
    #     print "candidate ens: " + str(len(all_inss.get_all()))
    #     print "relevant instances: " + str(len(rel_inss))
    #     print "irrelevant instances: " + str(len(irel_inss))
    #     return list(set(irel_inss + rel_inss))

# =============================================
# ================= Statistics ================
# =============================================
class TrainStats(object):
    """
    Statistics for CER train set.

    Attributes:
        instances: erd.ml.CERInstances
    """

    def __init__(self, instances):
        self.instances = instances

    def q_multi_inter(self):
        """ Returns number of instances with more than one main annotation. """
        query_dict = self.instances.group_by_query()
        q_multi_inter = 0
        for q_id, ins_list in query_dict.iteritems():
            rel_ins = 0
            for ins in ins_list:
                if ins.target == "1":
                    rel_ins += 1
            if rel_ins > 1:
                print q_id  # + "\t" + ins.q_content
                q_multi_inter += 1
        print "Queries with > 1 interpretations: " + str(q_multi_inter)
        return q_multi_inter

    def pos_ins_num(self):
        """ Returns number of positive instances in the train set. """
        pos_inss = []
        for ins in self.instances.get_all():
            if ins.target == "1":
                pos_inss.append(ins)
        print "Number of instances: " + str(len(self.instances.get_all()))
        print "Number of positive instances: " + str(len(pos_inss))
        return len(pos_inss)

    def q_num(self):
        """ Returns number of queries in the train set. """
        q_dict = defaultdict(list)
        for ins in self.instances.get_all():
            q_dict[ins.q_id].append(ins)
        q_num = len(q_dict.keys())
        print "Number of queries: " + str(q_num)
        return q_num

    # TODO: Test this function
    def avg_q_len(self):
        """ Returns average length of queries. """
        query_dict = self.instances.get_queries()
        leng = 0
        for q_content in query_dict.values():
            leng += len(q_content)
        avg_q_len = float(leng) / len(query_dict.keys())
        print "Avg. length of queries: " + str(avg_q_len)
        return avg_q_len


def main(args):
    """
    Generate CER train set.
    Required Args: -cer -d <data_name> -c <cmn> [-nof]
    """
    if args.commonness is None:
        raise Exception("Commonnness threshold is not defined.")

    # Reads groundtruth instances
    gt_json = econfig.RES_DIR + "/" + args.data + "-gt.json"
    gt_inss = CERInstances.from_json(gt_json)

    # Generates queries for the data set
    queries = None
    if args.data == "ysqle":
        queries = ysqle_gt.read_queries()
    elif args.data == "erd":
        queries = erd_gt.read_queries()
    elif args.data == "ysqle-erd":
        queries = ysqle_erd_gt.read_queries()
    elif args.data == "toy":
        queries = ysqle_erd_gt.read_queries(ysqle_erd_file=econfig.DATA_DIR + "/toy.tsv")

    filter_str = "" if args.filter else "-unfilter"
    # sf_source_str = "-" + args.sfsource if args.sfsource is not None else ""
    ts = TrainSetCER(args.commonness, args.sfsource)

    # Generates train set
    if args.trainset:
        # Generates train set and adds features
        train_inss = ts.gen_train_set(gt_inss, queries)
        # add_commonness(train_inss)
        if not args.nofeatures:
            RankerLTR.add_features(train_inss, args.commonness, args.sfsource)

        # Writes train set into file
        file_name = econfig.RES_DIR + "/" + args.data + "-cerTrain-c" + str(args.commonness) + filter_str
        if args.nofeatures:
            file_name += "-nof"
        train_inss.to_json(file_name + ".json")
        train_inss.to_str(file_name + ".txt")
        # train_inss.to_libsvm(file_name + ".libsvm")

    # Generates CV set
    elif args.cvset:
        file_name = econfig.EVAL_DIR + "/" + args.data + "-cerCV-c" + str(args.commonness) + filter_str
        cv_inss = ts.gen_cv_set(gt_inss, queries)
        cv_inss.to_json(file_name + ".json")
        # cv_inss.to_str(file_name + ".txt")
