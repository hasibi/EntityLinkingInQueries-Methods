"""
Uses Mixture of Language Models(MLM) to rank entities.
@author: Faegheh Hasibi
"""
from datetime import datetime
import math

from nordlys.erd.ml.cer_instances import CERInstances
from nordlys.erd.features.query_sim_feat import QuerySimFeat
from nordlys.erd import econfig
from nordlys.erd.groundtruth import erd_gt, ysqle_erd_gt, ysqle_gt
from nordlys.erd.query.query import Query


class RankerMLM(object):
    """
    Uses MLM to rank entities for the given query.
    Attributes:
        Weights: A list of float numbers denoting the weights for "title, links and catchall" fields.
        commonness_th: float, commonness threshold
        sf_source: surface form source
        filter: if True, filters entities not in the KB snapshot.
    """
    def __init__(self, weights, commonness_th=None, sf_source="facc", filter=None):
        self.weights = self.__get_weights(weights)
        self.commonness_th = commonness_th
        self.sf_source = sf_source
        self.filter = filter

    @staticmethod
    def __get_weights(weights):
        """ Gets MLM weights from the given array. """
        field_weights = {}
        if weights[0] != 0:
            field_weights['names'] = weights[0]
        if weights[1] != 0:
            field_weights['<dbo:wikiPageWikiLink>'] = weights[1]
        if weights[2] != 0:
            field_weights['contents'] = weights[2]
        return field_weights

    def rank_inss(self, instances, cmn):
        """
        Ranks instances using MLM method.

        :param instances: erd.ml.CERInstances
        :param cmn: if True, combines cmn with mlm score
        :return ranked instances
        """
        # Calculates MLM scores for each instance.
        print "Ranking CER instances ..."
        i = 0
        inss_by_query = instances.group_by_query()
        for qid in sorted(inss_by_query):
        # for ins in instances.get_all():
            inss_list = inss_by_query[qid]
            scores = []
            for ins in inss_list:
                score = QuerySimFeat(ins.q_content).nllr_mlm_score(ins.en_id, self.weights)  # .mlm_score
                if score is None:
                    ins.score = 0 # None
                    continue
                scores.append(score)
                if cmn:
                    cmn = ins.commonness if ins.commonness != 0 else 1e-5
                    score_with_cmn = math.log(score) + math.log(cmn)
                    # print score, ins.commonness, cmn, math.log(cmn)
                    ins.score = math.exp(score_with_cmn)
                else:
                    ins.score = score
                i += 1
                if i % 1000.0 == 0:
                    print "MLM score calculated until instance " + str(ins.id)
            # # Normalize by sum of scores
            # for ins in inss_list:
            #     print qid, ins.freebase_id, ins.score, max(scores) - min(scores),  # score_sum,
            #     score_sum = sum(scores)
            #     ins.score = score_sum if score_sum != 0 else ins.score
            #     print ins.score, "*******"
        return instances

    def rank_queries(self, queries, cmn, time_log_file=None):
        """
        Ranks queries (extracted from a dataset) with the given weights.

        :param queries: A dictionary of qid-query pairs: {q_id: q_content}
        :param cmn: if True, combines cmn with mlm score
        :param time_log_file: Write time log in a the file.
        :return erd.ml.CERInstances
        """
        print "Ranking queries ..."
        total_time = 0.0
        inss_list = []  # list of Instances
        s_t = datetime.now()  # start time
        for q_id, q_content in queries.iteritems():
            query = Query(q_id, q_content)
            q_inss = self.rank_query(query, cmn)
            if len(q_inss.get_all()) == 0:
                print "==================================================="
                print "No candidate entity found for query " + q_id + ", " + q_content
                print "==================================================="
            inss_list.append(q_inss)
        # time log
        e_t = datetime.now()
        diff = e_t - s_t
        total_time += diff.total_seconds()
        # save time logs
        time_log = "Execution time(min):\t" + str(round(total_time, 4)) + "\n"
        time_log += "Avg. time per query:\t" + str(round(total_time/len(queries), 4)) + "\n"
        print time_log
        # if time_log_file is not None:
        #     open(time_log_file + ".timelog", 'w').write(time_log)
        #     print "Time log:\t" + time_log_file + ".timelog"
        instances = CERInstances.concatenate_inss(inss_list)
        return instances

    def rank_query(self, query, cmn):
        """
        Generates ranking score for entities related to the given query.

        :param query: query.Query
        :param cmn: if True, combines cmn with mlm score
        :return erd.ml.CERInstances
        """
        q_inss = CERInstances.gen_instances(query, self.commonness_th, filter=self.filter, sf_source=self.sf_source)
        self.rank_inss(q_inss, cmn)
        return q_inss


def main(args):
    """
    Rank entities for the given query(ies).
    Required args: -mlm -rank -w <weights>
    Valid args: -in <input_file> -d <data_name> -qid <str> -query <str>
    """
    # sets default values
    args.weights = "0.2,0.0,0.8"
    args.commonness = 0.1

    weights = args.weights.replace(" ", "").split(',')
    weights = [float(x) for x in weights]
    ranker_mlm = RankerMLM(weights, commonness_th=args.commonness, sf_source=args.sfsource, filter=args.filter)
    # Ranks instances
    if args.input is not None:
        inss = CERInstances.from_json(args.input)
        ranked_inss = ranker_mlm.rank_inss(inss, args.cmn)
        # Writes instances
        cmn_str = "cmn-" if args.cmn else ""
        file_name = args.input[:args.input.rfind(".json")] + "-mlm-" + cmn_str + "-".join(map(str, weights))
        ranked_inss.to_json(file_name + ".json")
        ranked_inss.to_str(file_name + ".txt")
        ranked_inss.to_treceval(file_name, file_name + ".treceval")

    # Ranks queries
    else:
        if args.query is not None:
            queries = {args.qid: args.query}
            ranked_inss = ranker_mlm.rank_queries(queries, args.cmn)
            print ranked_inss.to_str()
        else:
            if args.data == "erd":
                queries = erd_gt.read_queries()
            elif args.data == "ysqle-erd":
                queries = ysqle_erd_gt.read_queries()
            elif args.data == "ysqle":
                queries = ysqle_gt.read_queries()
            elif args.data == "toy":
                queries = ysqle_erd_gt.read_queries(ysqle_erd_file=econfig.DATA_DIR + "/toy.tsv")

            # rank the query instances
            filter_str = "" if args.filter else "-unfilter"
            # sf_source_str = "-" + args.sfsource if args.sfsource is not None else ""
            cmn_str = "cmn-" if args.cmn else ""
            file_name = econfig.EVAL_DIR + "/" + args.data + "-c" + str(args.commonness) + \
                        "-mlm-" + cmn_str + "-".join(map(str, weights)) + filter_str
            ranked_inss = ranker_mlm.rank_queries(queries, args.cmn, time_log_file=None) #file_name)
            ranked_inss.to_json(file_name + ".json")
            # ranked_inss.to_str(file_name + ".txt")
            run_id = file_name[file_name.rfind("/")+1:]
            ranked_inss.to_treceval(run_id, file_name + ".treceval")