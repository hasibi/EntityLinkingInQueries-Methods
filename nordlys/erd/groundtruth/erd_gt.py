"""
Tools for generating ERD groundtruth.

@author: Faegheh Hasibi
"""
from collections import defaultdict
import config
from nordlys.erd import econfig
from nordlys.erd.econfig import ENTITY
from nordlys.erd.ml.cer_instances import CERInstances, CERInstance
from nordlys.entity.freebase.utils import FreebaseUtils
from nordlys.erd.query.query import Query


def parse_erd(erd_ann_file, erd_q_file):
    """
    Reads annotation file and add generates instances.
        - Considers only entities with dbpedia URI.
        - Example: One line of annotation file
            TREC-7	0	/m/04cnvy	bowflex	1

    Returns:
        erd.ml.CERInstances
    """
    not_founds = []
    queries = read_queries(erd_q_file)

    instances = CERInstances()
    ins_id = 0
    ann_file = open(erd_ann_file, "r")
    for line in ann_file:
        line = line.strip().split("\t")
        ins = CERInstance(ins_id)
        ins.target = "1"
        ins.q_id = line[0]
        ins.q_content = Query.preprocess(queries[line[0]]).lower()
        ins.set_id = line[1]
        ins.freebase_id = line[2]
        ins.mention = Query.preprocess(line[3]).lower()
        # set dbpedia id
        dbp_uri = econfig.ENTITY.fb_id_to_dbp_uri(line[2])
        ins.en_id = dbp_uri
        # considers only entities with dbpedia uri
        if dbp_uri is not None:
            instances.add_instance(ins)
        else:
            not_founds.append(line[2])
        ins_id += 1

    #writing not-found entities
    if len(not_founds) != 0:
        print "Freebase entities that are not found in mongoDB ..."
        print '\n'.join(not_founds)
    print "Number of ground truth instances:" + str(len(instances.get_all()))
    return instances


def read_queries(erd_q_file=config.ERD_QUERY, process=True):
    """
    Reads queries from Erd query file.

    Returns:
        A dictionary {query_id : query_content}
    """
    queries = {}
    q_file = open(erd_q_file, "r")
    for line in q_file:
        line = line.split("\t")
        query_id = line[0].strip()
        if process:
            query_content = Query.preprocess(line[-1].strip()).lower()
        else:
            query_content = line[-1].strip()
#            query = Query(query_id, query_content)
        queries[query_id] = query_content
    q_file.close()
    print "Numebr of queries:", len(queries)
    return queries


def gen_qrel_sets(file_name, use_wiki=False):
    """
    Generates qrel for interpretation sets.

    :param file_name: output file name
    :return: qid target en1 en2 ..
    """
    query_sets = {}  # {q_id:{set_id:[en1, en2, ..] , ...}, ...}
    # reads interpretation sets
    for qid, query in read_queries().iteritems():
        query_sets[qid] = defaultdict(list)

    ann_file = open(config.ERD_ANNOTATION, "r")  # format: qid   set_id  fb_id   mention label(=1)
    for line in ann_file:
        line = line.strip().split("\t")
        en_uri = line[2].strip()
        if use_wiki:
            dbp_uri = ENTITY.fb_id_to_dbp_uri(line[2].strip())
            en_uri = ENTITY.dbp_uri_to_wiki_uri(dbp_uri)
        query_sets[line[0].strip()][line[1].strip()].append(en_uri)

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
        gt_inss = parse_erd(config.ERD_ANNOTATION, config.ERD_QUERY)
        # writes Json and text format of groundtruth instances
        file_name = econfig.RES_DIR + "/" + args.data + "-gt"
        gt_inss.to_json(file_name + ".json")
        gt_inss.to_str(file_name + ".txt")
    if args.qrelsets:
        gen_qrel_sets(econfig.DATA_DIR + "/qrel_sets_" + args.data + "_wiki.txt", use_wiki=True)

