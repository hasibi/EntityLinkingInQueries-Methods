"""
Commonness baseline

@author: Faegheh Hasibi
"""
import argparse
from collections import defaultdict
from datetime import datetime
from nordlys.erd import econfig
from nordlys.erd.groundtruth import erd_gt, ysqle_erd_gt, ysqle_gt
from nordlys.erd.ml.cer_instances import CERInstance, CERInstances
from nordlys.erd.query.query import Mention, Query


class Commonness(object):
    def __init__(self, query, commonness_th=None, sf_source=None, filter=None):
        self.query = query
        self.all_ngrams = self.__ngram_by_len(query)
        self.cand_ens = {}
        self.commonness_th = commonness_th
        self.sf_source = sf_source
        self.filter = filter

    @staticmethod
    def __ngram_by_len(query):
        """
        Returns ngrams grouped by length.

        :param query: nordlys.erd.query
        :return: dictionary {1:["xx", ...], 2: ["xx yy", ...], ...}
        """
        ngrams_by_len = defaultdict(list)
        for ngram in query.get_ngrams():
            ngrams_by_len[len(ngram.split())].append(ngram)
        return ngrams_by_len

    def rank_ens(self):
        """Ranks queries based on commonness."""
        print "Ranking query " + self.query.id + " ..."
        # Get matched entities
        self.get_cand_ens(len(self.query.content.split()))

        # convert to CER instances
        inss = CERInstances()
        ins_id = 0
        for mention, matches in self.cand_ens.iteritems():
            for (dbp_uri, fb_id), cmn in matches.iteritems():
                ins = CERInstance(ins_id)
                ins.q_id = self.query.id
                ins.q_content = self.query.content
                ins.mention = mention
                ins.score = cmn
                ins.en_id = dbp_uri
                ins.freebase_id = fb_id
                ins_id += 1
                inss.add_instance(ins)
        return inss

    def get_cand_ens(self, n):
        """
        :param n: length of ngram
        :return: dictionary {(dbp_uri, fb_id):commonness, ..}
        """
        ngrams = self.all_ngrams[n]
        no_matches = True
        for ngram in ngrams:
            cand_ens = Mention(ngram, sf_source=self.sf_source).get_men_candidate_ens(self.commonness_th, filter=self.filter)
            if len(cand_ens) > 0:
                no_matches = False
                self.cand_ens[ngram] = cand_ens
                # print ngram, sorted(tuple(cand_ens.iteritems()), key=lambda item: item[1], reverse=True)
        if no_matches and n > 1:
            self.get_cand_ens(n-1)
        else:
            return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--commonness", help="Commonness threshold", type=float)
    parser.add_argument("-data", help="Data set name", choices=['ysqle', 'ysqle-erd', 'erd'])
    parser.add_argument("-unf", "--filter", help="Do not perform filtering", action="store_false", default=True)
    parser.add_argument("-sfs", "--sfsource", help="Surface form sources", choices=['facc', 'wiki'], default="facc")

    args = parser.parse_args()

    if args.data == "erd":
        queries = erd_gt.read_queries()
    elif args.data == "ysqle-erd":
        queries = ysqle_erd_gt.read_queries()
    elif args.data == "ysqle":
        queries = ysqle_gt.read_queries()

    s_t = datetime.now()  # start time
    total_time = 0.0

    # gets results for all queries
    inss_list = []
    for qid, query in queries.iteritems():
        cmn_ranker = Commonness(Query(qid, query), commonness_th=args.commonness, filter=args.filter, sf_source=args.sfsource)
        inss_list.append(cmn_ranker.rank_ens())
    cer_inss = CERInstances.concatenate_inss(inss_list)

    e_t = datetime.now()  # end time
    diff = e_t - s_t
    total_time += diff.total_seconds()
    time_log = "Execution time(min):\t" + str(total_time/60) + "\n"
    time_log += "Avg. time per query:\t" + str(total_time/len(queries))
    print time_log

    # converts to treceval
    filter_str = "" if args.filter else "-unfilter"
    run_id = "cmns-" + args.data + "-c" + str(args.commonness) + filter_str
    file_name = econfig.OUTPUT_DIR + "/eval/" + run_id
    cer_inss.to_treceval(run_id, file_name + ".treceval")
    cer_inss.to_json(file_name + ".json")
    open(file_name + ".timelog", "w").write(time_log)
    print len(cer_inss.get_all())


if __name__ == "__main__":
    main()