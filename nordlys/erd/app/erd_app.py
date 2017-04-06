"""
ERD application:
- Generates interpretation sets for a given query
- Calculates latency of the system for the given set of queries

@author: Faegheh Hasibi
"""
import argparse
import json
import pickle
from datetime import datetime

from nordlys.erd import econfig
from nordlys.erd.baselines.tagme import Tagme
from nordlys.erd.baselines.tagme_api import TagmeAPI
from nordlys.erd.isf.greedy import Greedy
from nordlys.erd.ml.cer_instances import CERInstance
from nordlys.erd.ml.isf_instances import ISFInstances
from nordlys.erd.query.query import Query
from nordlys.erd.cer.ranker_mlm import RankerMLM
from nordlys.erd.cer.ranker_ltr import RankerLTR
from nordlys.erd.isf.set_generator import SetGen
from nordlys.erd.isf.set_detector import SetDetect
from nordlys.erd.groundtruth import erd_gt, ysqle_erd_gt


class ERD(object):
    """
    Performs ERD for single queries
    Attributes:
        args: Required arguments for ERD
            - commonness-threshold
            - MLM-weights or trained ranker
            - K
            - Trained classifier
        isf_model: the trained model for entity ranking.
        isf_model: the trained classifier for set detection.
    """

    def __init__(self, args):
        self.args = args
        self.ranker = self.load_ranker(args)
        self.iset_classifier = self.load_classifier(args)
        if args.tagmeapi:
            self.baseline = TagmeAPI()
            self.tagme_annots = json.load(open(econfig.OUTPUT_DIR + "/baselines/tagme_erd-test.json"))

    @classmethod
    def load_ranker(cls, args):
        """ Loads MLM or LTR ranker. """
        ranker = None
        if args.weights is not None:
            weights = args.weights.replace(" ", "").split(',')
            ranker = RankerMLM([float(x) for x in weights], commonness_th=args.commonness, sf_source=args.sfsource, filter=True)
        elif args.cermodel is not None:
            model = open(args.cermodel, "r").read()
            ranker = RankerLTR(model=pickle.loads(model), commonness_th=args.commonness, sf_source=args.sfsource, filter=True)
        return ranker

    @classmethod
    def load_classifier(cls, args):
        """ Loads the classifier for set detection. """
        if args.isfmodel is not None:
            model = open(args.isfmodel, "r").read()
            return SetDetect(model=pickle.loads(model))
        else:
            return None

    def process_query(self, q_id, q_content):
        """
        Process a single query through the whole pipeline and generates interpretation sets.

        Args:
            q_id, q_content: str

        Returns:
            interpretation sets in format of ERD webservice
        """
        print "=================================="
        print "processing query " + q_id + "..."
        # ====== Baselines ======
        if self.args.tagmeapi:
            query_annots = self.tagme_annots.get(q_id, None)
            if query_annots is None:
                print "ERROR: Query id \"" + q_id + "\" is not found!!"
                return ISFInstances({})
            return self.baseline.process_query(q_id, q_content, tagme_annots=query_annots,
                                               threshold=self.args.threshold, filter=True)
        if self.args.tagme:
            tagme = Tagme(Query(q_id, q_content), self.args.threshold)
            return tagme.process_query()

        # ====== CER step ======
        query = Query(q_id, q_content)
        if self.args.weights is not None:
            q_inss = self.ranker.rank_query(query, self.args.cmn)
        else:
            q_inss = self.ranker.rank_query(query)
        # ====== ISF step ======
        if self.args.greedy:
            greedy = Greedy(self.args.threshold) #self.args.sth, self.args.rth)
            isf_inss = greedy.gen_isf_inss(q_inss)
        elif self.args.greedytop:
            greedy_top = GreedyTop(self.args.threshold)
            isf_inss = greedy_top.gen_isf_inss(q_inss)
        else:
            # candidate set generation
            generator = SetGen(q_inss, self.args.k)
            isf_inss = generator.gen_isf_inss()
            # set detection
            isf_inss = self.iset_classifier.predict(isf_inss)#, threshold=self.args.threshold)
        return isf_inss

    def process_queries(self, queries, time_log_file=None):
        """ Find interpretation sets for the queries and calculates end-to-end processing time.
        Args:
            queries: Dictionary of queries
            time_log_file: String, name of file to save the time log.
        """
        s_t = datetime.now()  # start time
        total_time = 0.0

        # Processing all queries
        inss_list = []
        for q_id, q_content in queries.iteritems():
            q_inss = self.process_query(q_id, q_content)
            inss_list.append(q_inss)

        #time log
        e_t = datetime.now()  # end time
        diff = e_t - s_t
        total_time += diff.total_seconds()
        time_log = "Execution time(min):\t" + str(round(total_time/60, 4)) + "\n"
        time_log += "Avg. time per query:\t" + str(round(total_time/len(queries), 4)) + "\n"
        print time_log
        if time_log_file is not None:
            open(time_log_file, 'w').write(time_log)
            print "Time log:\t" + time_log_file

        return ISFInstances.concatenate_inss(inss_list)


def to_erd_protocol(instances):
    """
    Convert instances to the ERD output format
    Returns:
        Tab delimited string in the following format:
           QueryID    InterpretationSet    PrimaryID    MentionText    Score
    """
    print "instances to erd output protocol ..."
    # out = ""
    # inss_by_query = instances.group_by_query()
    # for qid in sorted(inss_by_query.keys()):
    #     set_id = 0
    #     inss_list = inss_by_query[qid]
    #     ins_score = [(ins.id, ins.score) for ins in inss_list]
    #     for (ins_id, _) in sorted(ins_score, key=lambda item: item[1], reverse=True):  #inss_list:
    #         ins = instances.get_instance(ins_id)
    #         # if ins.score < 0.3:
    #         #     break
    #         for en_id, mention in ins.inter_set.iteritems():
    #             out += qid + "\t" + str(set_id) + "\t" + \
    #                 CERInstance.gen_freebase_id(en_id) + "\t" + \
    #                 mention + "\t" + str(ins.score) + "\n"
    #         break
    # k = out.rfind("\n")
    # return out[:k]

    out = ""
    inss_by_query = instances.group_by_query()
    for q_id, ins_list in inss_by_query.iteritems():
        unique_entries = set()
        set_id = 0
        for ins in ins_list:
            if str(ins.target) == "1":
                entry = tuple(sorted(ins.inter_set.keys()))
                if entry not in unique_entries:
                    for en_id, mention in ins.inter_set.iteritems():
                        out += q_id + "\t" + str(set_id) + "\t" + CERInstance.gen_freebase_id(en_id) + "\t" + mention + \
                               "\t" + str(ins.score) + "\n"
                    set_id += 1
                    unique_entries.add(entry)
    k = out.rfind("\n")
    return out[:k]


def read_args():
    """ Parses input arguments and returns parsed arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--commonness", help="Commonness threshold", type=float)
    parser.add_argument("-k", help="top-K entities to be considered from CER step", type=float)
    parser.add_argument("-w", "--weights", help="MLM weights", type=str)
    parser.add_argument("-cm", "--cermodel", help="Trained model file for CER step", type=str)
    parser.add_argument("-im", "--isfmodel", help="Trained model file for ISF step", type=str)
    parser.add_argument("-runid", help="Run id", type=str)
    parser.add_argument("-cmn", help="MLM-cmn method for entity ranking", action="store_true", default=False)
    parser.add_argument("-sfs", "--sfsource", help="Surface form sources", choices=['facc', 'wiki'])

    parser.add_argument("-tagmeapi", help="TagMe API results", action="store_true", default=False)
    parser.add_argument("-tagme", help="TagMe baseline", action="store_true", default=False)
    parser.add_argument("-greedy", help="ISF using greedy approach", action="store_true", default=False)
    parser.add_argument("-greedytop", help="ISF using greedy-top approach", action="store_true", default=False)
    parser.add_argument("-th", "--threshold", help="Score threshold for pruning entities", default=None, type=float)
    parser.add_argument("-ver", "--version", help="CI, CD or both versions", choices=['ci', 'cd', 'cid'], default='cid')
    # parser.add_argument("-sth", help="Score threshold for greedy approach", default=None, type=float)
    # parser.add_argument("-rth", help="Rel_score threshold for greedy approach", default=None, type=float)

    parser.add_argument("-data", help="Data set name", choices=['ysqle', 'ysqle-erd', 'erd'])
    parser.add_argument("-qid", help="Query id", type=str)
    parser.add_argument("-query", help="query text", type=str)

    args = parser.parse_args()

    # set default values
    if args.data is None:
        args.data = "ysqle-erd"

    return args


def take_action(args):
    erd = ERD(args)
    # Processing single query
    if args.query is not None:
        inss = erd.process_query(args.qid, args.query)
        print to_erd_protocol(inss)

    # processing queries of a data set
    else:
        if args.data == "erd":
            queries = erd_gt.read_queries()
        elif args.data == "ysqle-erd":
            queries = ysqle_erd_gt.read_queries()

        run_id = __gen_run_id(args) + "-app"
        # run_id += "-qd"
        inss = erd.process_queries(queries, econfig.EVAL_DIR + "/" + run_id + ".timelog")
        # inss.to_str(econfig.EVAL_DIR + "/" + run_id + ".txt")
        inss.to_erdeval(econfig.EVAL_DIR + "/" + run_id + ".erdeval")
        inss.to_json(econfig.EVAL_DIR + "/" + run_id + ".json")


def __gen_run_id(args):
    run_id = args.data + "-c" + str(args.commonness)
    run_id += "-" + args.sfsource if args.sfsource is not None else ""

    cmn_str = "cmn-" if args.cmn else ""
    if args.weights is not None:
        run_id += "-mlm-" + cmn_str + args.weights.replace(" ", "").replace(",", "-")
    else:
        run_id += "-ltr" + args.cermodel[args.cermodel.rfind("-t"):args.cermodel.rfind(".model")]

    if args.greedy:
        run_id += "-greedy-" + str(args.threshold) #-s" + str(args.sth) + "-r" + str(args.rth)
    else:
        run_id += "-k" + str(int(args.k))
        run_id += args.isfmodel[args.isfmodel.rfind("-t"):args.isfmodel.rfind(".model")]
    return run_id


if __name__ == '__main__':
    take_action(read_args())