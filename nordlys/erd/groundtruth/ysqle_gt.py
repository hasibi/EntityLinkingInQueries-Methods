"""
Tools for generating YSQLE groundtruth.

@author: Faegheh Hasibi
"""
from collections import defaultdict
import csv
from urllib import quote
import xml.etree.ElementTree as ETree
import sys

import config
from nordlys.erd import econfig
from nordlys.erd.ml.cer_instances import CERInstances, CERInstance
from nordlys.erd.query.query import Query


def __to_dbpedia_uri(entity_id):
    """
    Converts Wikipedia url to dbpedia uri
        e.g. http://en.wikipedia.org/wiki/costs -> <dbpedia:costs>
    """
    k = entity_id.rfind('/wiki/')
    # to convert to precent encoding, we use qoute(str)
    uri = "<dbpedia:" + quote(entity_id[k+6:], '!$&\'()*+,-./:;=@_~') + ">"
    return uri


def ysqle_to_tsv(ysqle_file, out_file):
    """
    Parse the Yahoo! Webscope data (YSQLE) and generate tsv file.
    - wiki ids are converted to dbpedia uris .e.g. <dbpedia:costs>.
    - freebase Ids are added


    :param ysqle_file: YSQLE data file (original XML file)
    :param out_file: tsv file to write the output
    :return output string of tsv file
    """
    print "Parsing Yahoo! webscope data ..."
    query_annots = defaultdict(list)  # {(qid, text):[], ...}
    tree = ETree.parse(ysqle_file)
    root = tree.getroot()
    for session in root:
        session_id = session.attrib['id'].strip()
        query_num = 1
        # read queries
        for query in session:
            query_id = session_id + "_" + str(query_num)
            # read annotations of each query (or entities)
            for annotate in query:
                if annotate.tag == "text":
                    query_text = annotate.text.strip()
                    query_annots[(query_id, query_text)] = []
                elif annotate.tag == "annotation":
                    annotation = {}
                    if annotate.attrib['main'] == "true":
                        annotation['label'] = "1"
                    else:
                        annotation['label'] = "0"
                    # read entity mention and wiki id
                    for child in annotate:
                        if child.tag == "span":
                            annotation['mention'] = child.text.strip()
                        elif child.tag == "target":
                            annotation['dbp_uri'] = __to_dbpedia_uri(child.text.strip().encode('utf-8'))
                            fb_id = CERInstance.gen_freebase_id(annotation['dbp_uri'])
                            annotation['fb_id'] = "" if fb_id is None else fb_id
                    query_annots[(query_id, query_text)].append(annotation)
            query_num += 1

    # write as a tsv file
    str_out = "qid\tquery\tmention\tentity\ttarget\tfreebase_id\n"
    sorted_queries = sorted(query_annots.keys(), key=lambda item: item[0])
    for (qid, q_content) in sorted_queries:
        annots = query_annots[(qid, q_content)]
        if len(annots) == 0:
            str_out += qid + "\t" + q_content + "\n"
            continue
        for annot in annots:
            str_out += qid + "\t" + q_content + "\t" + annot['mention'] + "\t" + annot.get('dbp_uri', "") + "\t" + \
                       annot['label'] + "\t" + annot.get('fb_id', "") + "\n"
    open(out_file, "w").write(str_out)
    print "TSV file: " + out_file
    print "Number of queries: ", len(query_annots)
    return str_out


def parse_ysqle(ysqle_tsv_file):
    """
    Parses YSQLE queries and generates instnaces

    format: Label queryID Query Mention Dbpedia Uri SetID FbID

    :param ysqle_tsv_file: qid	query	mention	entity	target	freebase_id
    :return: CER instances
    """
    instances = CERInstances(None)
    ins_id = 0
    query_sets = set()
    query_sets_all = set()
    with open(ysqle_tsv_file, 'rb') as ysqle:
        reader = csv.DictReader(ysqle, delimiter="\t", quoting=csv.QUOTE_NONE)

        # Reads tsv lines
        for line in reader:
            query_sets_all.add(line['qid'])
            if (line['freebase_id'] is None) or (line['freebase_id'].strip() == ""):
                continue
            query_sets.add(line['qid'])
            ins = CERInstance(ins_id)
            ins.q_id = line['qid']
            ins.q_content = Query.preprocess(line['query']).lower()
            ins.mention = Query.preprocess(line['mention']).lower()
            ins.en_id = line['entity']
            ins.target = line['target']
            ins.freebase_id = line.get('freebase_id', None)
            instances.add_instance(ins)
            ins_id += 1
    print "\t#All Queries:            " + str(len(query_sets_all))
    print "\t#Ground truth instances: " + str(len(instances.get_all()))
    print "\t#Groundtruth queries:    " + str(len(query_sets))
    return instances


def read_queries(ysqle_tsv_file=config.YSQLE, process=True):
    """
    Reads queries from TSV file.

    :return A dictionary {query_id : query_content}
    """
    queries = {}
    with open(ysqle_tsv_file, 'rb') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter="\t", quoting=csv.QUOTE_NONE)

        for line in reader:
            # if (line.get('entity', None) is not None) and (line['entity'].strip() != ""):
            if process:
                queries[line['qid']] = Query.preprocess(line['query'].strip()).lower()
            else:
                queries[line['qid']] = line['query'].strip()
    print "Number of queries:", len(queries)
    return queries


def gen_qrel(ysqle_tsv_file, file_name, use_dbp=True):
    """Generates qrel."""
    qrel_str = ""
    print "Generates DBPedia Qrel ..."
    unique_entries = set()
    en_label = "entity" if use_dbp else "freebase_id"
    with open(ysqle_tsv_file, 'rb') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter="\t", quoting=csv.QUOTE_NONE)

        for line in reader:
            en_id = line.get(en_label, None)
            # if (en_id is not None) and (line['entity'].strip() != "") and ((line['qid'], en_id) not in unique_entries):
            if (line.get('freebase_id', None) is not None) and (line['freebase_id'].strip() != "") and \
                    ((line['qid'], en_id) not in unique_entries) and (line['target'] == "1"):
                qrel_str += line['qid'] + "\t0\t" + en_id + "\t" + line['target'] + "\n"
                unique_entries.add((line['qid'], en_id))
    open(file_name, 'w').write(qrel_str)
    print "Qrel file" + file_name


def main(args):
    """
    Generates groundtruth instances and the qrel files.
    Required args: --data <data_name> [--qrel]
    """
    if args.gt:
        gt_inss = parse_ysqle(config.YSQLE)
        file_name = econfig.RES_DIR + "/" + args.data + "-gt"
        gt_inss.to_json(file_name + ".json")
        gt_inss.to_str(file_name + ".txt")
    if args.qrelsets:
        gen_qrel(config.YSQLE, config.DATA_DIR + "/tagme/" + "qrel_ysqle-dbp.txt", use_dbp=True)
        # gen_qrel(config.YSQLE, econfig.DATA_DIR + "/" + "qrel_ysqle-fb.txt", use_dbp=False)


if __name__ == "__main__":
    main(sys.argv[1:])


#  =============================================================================================
#  =========== These codes are used to generate the initial query set for Y-erd ================
#  =============================================================================================

# def main(args):
#     gt_inss = None
#     if args.data == "ysqle":
#         gt_inss = parse_ysqle(config.YSQLE)
#         gt_inss = preprocess_gt(gt_inss)
#
#     # writes json and text format of ground truth
#     file_name = econfig.RES_DIR + "/" + args.data + "-gt"
#     gt_inss.to_json(file_name + ".json")
#     gt_inss.to_str(file_name + ".txt")

# def parse_ysqle(ysqle_file):
#     """
#     Parse the Yahoo! Webscope data (YSQLE) and generate instances.
#     Pre-processing:
#         - wiki ids are converted to dbpedia uris .e.g. <dbpedia:costs>.
#
#     Args:
#         ysqle_file: YSQLE data file (original XML file)
#
#     Returns:
#         erd.ml.CERInstances
#     """
#     print "Parsing Yahoo! webscope data ..."
#     instances = CERInstances()
#     ins_id = 0
#     tree = ETree.parse(ysqle_file)
#     root = tree.getroot()
#     for session in root:
#         session_id = session.attrib['id']
#         query_num = 1
#         # read queries
#         for query in session:
#             query_id = session_id + "_" + str(query_num)
#             query_text = ""
#             # read annotations of each query (or entities)
#             for annotate in query:
#                 if annotate.tag == "text":
#                     query_text = annotate.text
#                 elif annotate.tag == "annotation":
#                     # Generate instance
#                     instance = CERInstance(ins_id)
#                     instance.q_id = query_id
#                     instance.q_content = query_text
#                     # Consider main annotations as positive instances
#                     if annotate.attrib['main'] == "true":
#                         instance.target = "1"
#                     else:
#                         instance.target = "0"
#                     # read entity mention and wiki id
#                     for child in annotate:
#                         if child.tag == "span":
#                             instance.mention = child.text
#                         elif child.tag == "target":
#                             instance.en_id = __to_dbpedia_uri(child.text.encode('utf-8'))
#                             instances.add_instance(instance)
#                             ins_id += 1
#             query_num += 1
#     print "--------- Yahoo! Webscope Statistics ---------"
#     print "Number of instances: " + str(len(instances.get_all()))
#     print "Number of queries: " + str(len(instances.get_queries()))
#     return instances


# def preprocess_gt(instances):
#     """
#     pre-process YSQLE instances.
#     pre-processing consists of:
#        # - Removing special characters from queries and mentions.
#        # - convert query and mentions to lower case.
#         - Deleting instances that are not in the KB snapshot.
#         - Add freebase Id to the instances
#         - Assign default interpretation set (0) to entities.
#
#     Args:
#         instances: erd.ml.CERInstances, Yahoo groundtruth instances
#
#     Returns:
#         erd.ml.CERInstances, Processed and filtered instances.
#      """
#     not_founds = []  # set()
#     p_instances = CERInstances(None)
#     ins_id = 0
#     for ins in instances.get_all():
#         # Adds only wiki entities that are in the KB snnapshot
#         if ins.en_id not in econfig.KB_SNP_DBP:
#             not_founds += [ins.en_id]
#             continue
#         entity = econfig.ENTITY.lookup_dbpedia_uri(ins.en_id)
#         if entity is None:
#             raise Exception("Entity should not be None!!")
#         fb_id = CERInstance.gen_freebase_id(ins.en_id)
#         p_ins = CERInstance(ins_id)
#         p_ins.q_id = ins.q_id
#         p_ins.q_content = ins.q_content
#         Query.rm_stop_chars(ins.q_content).lower()
#         p_ins.mention = ins.mention
#         Query.rm_stop_chars(ins.mention).lower()
#         p_ins.en_id, p_ins.freebase_id = ins.en_id, fb_id
#         p_ins.target = ins.target
#         p_ins.set_id = "0" if p_ins.target == "1" else "-1"
#         p_instances.add_instance(p_ins)
#         ins_id += 1
#     # write not found entities
#     nf_file = open(econfig.RES_DIR + "/not_founds_ysqle.txt", 'w')
#     out = "Not found entities:\n" + '\n'.join(not_founds)
#     nf_file.write(out)
#     print "--------- Yahoo! Webscope Statistics (pre-processed) ---------"
#     print "Number of instances:" + str(len(p_instances.get_all()))
#     print "Number of queires: " + str(len(p_instances.get_queries()))
#     return p_instances






