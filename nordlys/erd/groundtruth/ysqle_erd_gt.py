"""
Tools for generating YSQLE-erd groundtruth.

@author: Faegheh Hasibi
"""
from collections import defaultdict
import csv

import config
from nordlys.erd import econfig
from nordlys.erd.econfig import ENTITY
from nordlys.erd.ml.cer_instances import CERInstances, CERInstance
from nordlys.erd.query.query import Query


def parse_ysqle_erd(ysqle_erd_file):
    """
    Reads YSQLE-erd data and generated instances.

    :param y_file: file name, format: difficulty	qid	query	mention	entity	set_id	freebase_id
    :return erd.ml.CERInstances
    """
    instances = CERInstances(None)
    ins_id = 0
    query_sets = set()
    query_sets_all = set()
    with open(ysqle_erd_file, 'rb') as ysqle_erd:
        reader = csv.DictReader(ysqle_erd, delimiter="\t", quoting=csv.QUOTE_NONE)

        # Reads tsv lines
        for line in reader:
            query_sets_all.add(line['qid'])
            if (line['entity'] is None) or (line.get('entity', "").strip() == ""):
                continue
            query_sets.add(line['qid'])
            ins = CERInstance(ins_id)
            ins.q_id = line['qid']
            ins.q_content = Query.preprocess(line['query']).lower()
            ins.mention = Query.preprocess(line['mention']).lower()
            ins.en_id = line['entity']
            ins.target = "1"
            ins.set_id = line['set_id']
            ins.freebase_id = line['freebase_id']
            instances.add_instance(ins)
            ins_id += 1
    print "\t#All Queries:            " + str(len(query_sets_all))
    print "\t#Ground truth instances: " + str(len(instances.get_all()))
    print "\t#Groundtruth queries:    " + str(len(query_sets))
    return instances


def read_queries(ysqle_erd_file=config.YSQLE_ERD, process=True):
    """
    Reads queries from Erd query file.

    Returns:
        A dictionary {query_id : query_content}
    """
    queries = {}
    with open(ysqle_erd_file, 'rb') as ysqle_erd:
        reader = csv.DictReader(ysqle_erd, delimiter="\t", quoting=csv.QUOTE_NONE)

        for line in reader:
            qid = line['qid']
            query = line['query'] #yerd_spell_corrected[qid] if qid in yerd_spell_corrected else line['query']
            if process:
                queries[qid] = Query.preprocess(query.strip()).lower()
            else:
                queries[qid] = query.strip()
    print "Number of queries:", len(queries)
    return queries


def gen_qrel_sets(file_name, ysqle_erd_file=config.YSQLE_ERD, use_wiki=False):
    """
    Generates qrel for interpretation sets.

    :param file_name: output file name
    :param ysqle_erd_file:  format -> difficulty	qid	query	mention	entity	set_id	freebase_id
    :return: qid target en1 en2 ..
    """
    query_sets = dict()  # {q_id:{set_id:[en1, en2, ..] , ...}, ...}
    with open(ysqle_erd_file, 'rb') as ysqle_erd:
        reader = csv.DictReader(ysqle_erd, delimiter="\t", quoting=csv.QUOTE_NONE)

        for line in reader:
            qid = line['qid']
            if qid not in query_sets:
                query_sets[qid] = defaultdict(list)
            set_id = line.get('set_id', "")
            if (line.get('set_id', None) is not None) and (line['set_id'] != ""):
                en_uri = line['freebase_id']
                if use_wiki:
                    dbp_uri = ENTITY.fb_id_to_dbp_uri(line['freebase_id'].strip())
                    en_uri = ENTITY.dbp_uri_to_wiki_uri(dbp_uri)

                query_sets[qid][set_id].append(en_uri)

    # writes the interpretation sets to the file
    out_str = ""
    for qid in sorted(query_sets.keys()):
        print qid, query_sets[qid]
        if len(query_sets[qid]) == 0:
            out_str += qid + "\n"
        else:
            for iset in query_sets[qid].values():
                out_str += qid + "\t" + "1\t" + "\t".join(iset) + "\n"

    open(file_name, 'w').write(out_str)
    print "Qrel_sets is written to " + file_name


def main(args):
    """
    Generates groundtruth instances:
    Required args:  --data erd
    """
    if args.gt:
        if args.data == "toy":
            gt_inss = parse_ysqle_erd(econfig.DATA_DIR + "/toy.tsv")
        else:
            gt_inss = parse_ysqle_erd(config.YSQLE_ERD)
        # writes Json and text format of groundtruth instances
        file_name = econfig.RES_DIR + "/" + args.data + "-gt"
        gt_inss.to_json(file_name + ".json")
        gt_inss.to_str(file_name + ".txt")
    if args.qrelsets:
        gen_qrel_sets(econfig.DATA_DIR + "/qrel_sets_" + args.data + "_wiki.txt", use_wiki=True)

yerd_spell_corrected = {
    "yahoo-112_2": "childfund",
    "yahoo-121_1": "firefox",
    "yahoo-139_3": "dwyane wade and gabrielle union",
    "yahoo-148_2": "gmail",
    "yahoo-229_1": "travis porter",
    "yahoo-254_4": "dodge",
    "yahoo-348_1": "my yahoo mail",
    "yahoo-352_4": "barack obama girl",
    "yahoo-371_2": "century 21 real estate",
    "yahoo-371_3": "merrell shoes",
    "yahoo-385_4": "papa john's restaurant",
    "yahoo-436_3": "best buy",
    "yahoo-436_4": "best buy black friday",
    "yahoo-436_5": "best buy laptops",
    "yahoo-459_1": "occitane",
    "yahoo-477_1": "facebook",
    "yahoo-502_18": "tainio",
    "yahoo-523_13": "new york governor paterson",
    "trec-2011-66_4": "yellow tail wine australia",
    "trec-2012-25_1": "when france win world cup",
    "trec-2013-31_7": "churchill downs",
    "trec-2013-31_8": "churchill downs seating chart",
    "trec-2010-135_1": "solarone",
    "yahoo-409_6": "youtube",
    "yahoo-15_1": "mimio board",
}