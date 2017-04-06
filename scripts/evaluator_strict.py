"""
This script evaluates query interpretations based on the strict evaluation metrics;
macro averaging of precision, recall and F-measure.

For detailed information see:
    F. Hasibi, K. Balog, and S. E. Bratsberg. "Entity Linking in Queries: Tasks and Evaluation",
    In Proceedings of ACM SIGIR International Conference on the Theory of Information Retrieval (ICTIR '15), Sep 2015.
    DOI: http://dx.doi.org/10.1145/2808194.2809473

Usage:
    python evaluation_erd.py <qrel_file> <result_file>
e.g.
    python evaluation_erd.py qrels_sets_ERD-dev.txt ERD-dev_MLMcg-GIF.txt


@author: Faegheh Hasibi (faegheh.hasibi@idi.nunu.no)
"""

from __future__ import division

import argparse
import sys
from collections import defaultdict


class Evaluator(object):

    def __init__(self, qrels, results, q=False):
        self.qrels = qrels
        self.results = results
        self.q = q

        self.qrels_dict = self.__group_by_queries(self.parse_file(qrels))
        self.results_dict = self.__group_by_queries(self.parse_file(results))
        qid_overlap = set(self.qrels_dict.keys()) & set(self.results_dict.keys())
        if len(qid_overlap) == 0:
            print "ERR: Query mismatch between qrel and result file!"
            exit(0)

    @staticmethod
    def parse_file(file_name):
        """
        Parses file and returns the positive instances for each query.

        :param file_name: Name of file to be parsed
        :return list of lines [[qid, label, en_id, ...], ...]
        """
        file_lines = []
        efile = open(file_name, "r")
        for line in efile.readlines():
            if line.strip() == "":
                continue
            cols = line.strip().split("\t")
            file_lines.append(cols)
        return file_lines

    @staticmethod
    def __group_by_queries(file_lines):
        """
        Groups the lines by query id.

        :param file_lines: list of lines [[qid, label, en_id, ...], ...]
        :return: {qid: [iset0, iset1, ..], ..}; isets are sets of entity ids
        """
        grouped_inters = defaultdict(list)
        for cols in file_lines:
            if len(cols) > 2:
                grouped_inters[cols[0]].append(set(cols[2:]))
            elif cols[0] not in grouped_inters:
                grouped_inters[cols[0]] = []

        # check that identical interpretations are not assigned to a query
        for qid, interprets in grouped_inters.iteritems():
            q_interprets = set()
            for inter in interprets:
                if tuple(sorted(inter)) in q_interprets:
                    print "Err: Identical interpretations for query [" + qid + "]!"
                    exit(0)
                else:
                    q_interprets.add(tuple(sorted(inter)))
        return grouped_inters

    def eval(self, eval_query_func):
        """
        Evaluates all queries and calculates total precision, recall and F1 (macro averaging).

        :param eval_query_func: A function that takes qrel and results for a query and returns evaluation metrics
        :return  Total precision, recall, and F1 for all queries
        """
        queries_eval = {}
        total_prec, total_rec, total_f = 0, 0, 0
        for qid in sorted(self.qrels_dict):
            queries_eval[qid] = eval_query_func(self.qrels_dict[qid], self.results_dict.get(qid, []))
            total_prec += queries_eval[qid]['prec']
            total_rec += queries_eval[qid]['rec']
        n = len(self.qrels_dict)  # number of queries
        total_prec /= n
        total_rec /= n
        total_f = (2 * total_rec * total_prec) / (total_rec + total_prec) if total_prec + total_rec != 0 else 0

        log = "\n----------------" + "\nEvaluation results:\n" + \
              "Prec: " + str(round(total_prec, 4)) + "\n" +\
              "Rec:  " + str(round(total_rec, 4)) + "\n" + \
              "F1:   " + str(round(total_f, 4)) + "\n" + \
              "all:  " + str(round(total_prec, 4)) + ", " + str(round(total_rec, 4)) + ", " + str(round(total_f, 4))
        print log
        if self.q:
            self.write_query_eval(queries_eval)
        metrics = {'prec': total_prec, 'rec': total_rec, 'f': total_f}
        return metrics

    def write_query_eval(self, queries_eval):
        """Writes query level evaluation in a tab separated file: query_id  p   r   f """
        out_str = "qid\tp\tr\tf"
        for qid, metrics in queries_eval.items():
            out_str += "\n" + qid + "\t" + str(metrics["prec"]) + "\t" + str(metrics['rec']) + "\t" + str(metrics['f'])

        file_name = self.results[:self.results.rfind(".")] + "_" + \
                    self.qrels[self.qrels.rfind("/") + 1: self.qrels.rfind(".")] + "_sig.csv"
        open(file_name, "w").write(out_str)
        print "Query evaluation file:", file_name


def erd_eval_query(query_qrels, query_results):
    """
    Evaluates a single query.

    :param query_qrels: Query interpretations from Qrel [{en1, en2, ..}, ..]
    :param query_results: Query interpretations from result file [{en1, en2, ..}, ..]
    :return: precision, recall, and F1 for a query
    """
    tp = 0  # correct
    fn = 0  # missed
    fp = 0  # incorrectly returned

    # ----- Query has no interpretation set. ------
    if len(query_qrels) == 0:
        if len(query_results) == 0:
            return {'prec': 1, 'rec': 1, 'f': 1}
        return {'prec': 0, 'rec': 0, 'f': 0}

    # ----- Query has at least an interpretation set. -----
    # Iterate over qrels to calculate TP and FN
    for qrel_item in query_qrels:
        if find_item(qrel_item, query_results):
            tp += 1
        else:
            fn += 1
    # Iterate over results to calculate FP
    for res_item in query_results:
        if not find_item(res_item, query_qrels):  # Finds the result in the qrels
            fp += 1

    prec = tp / (tp+fp) if tp+fp != 0 else 0
    rec = tp / (tp+fn) if tp+fn != 0 else 0
    f = (2 * prec * rec) / (prec + rec) if prec + rec != 0 else 0
    metrics = {'prec': prec, 'rec': rec, 'f': f}
    return metrics


def find_item(item_to_find, items_list):
    """
    Returns True if an item is found in the item list.

    :param item_to_find: item to be found
    :param items_list: list of items to search in
    :return boolean
    """
    is_found = False
    item_to_find = set(item_to_find)

    for item in items_list:
        if set(item) == item_to_find:
            is_found = True
    return is_found


def main(args):
    if len(args) < 2:
        print "\tUsage: [qrel_file] [result_file] [-q]"
        exit(0)
    qrels = args[0]
    results = args[1]
    q = True if len(args) > 2 else False
    evaluator = Evaluator(qrels, results, q)
    evaluator.eval(erd_eval_query)

if __name__ == '__main__':
    main(sys.argv[1:])
