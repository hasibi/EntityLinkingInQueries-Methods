"""
This is the main entry point for command line usage of groundtruth package.

Functionality:
- Generates JSON format og groundtruth instances.
- Generates trec-eval qrels.

Data support:
- ERD dataset
- YSQLE
- YSQLE-erd

See the detailed description at [wiki/groundtruth] (https://bitbucket.org/kbalog/nordlys-erd/wiki/groundtruth)

@author: Faegheh Hasibi
"""

import argparse
from nordlys.erd import econfig
from nordlys.erd.groundtruth import erd_gt
from nordlys.erd.groundtruth import ysqle_gt
from nordlys.erd.groundtruth import ysqle_erd_gt
from nordlys.erd.ml.cer_instances import CERInstances


def gen_qrel(instances, file_name):
    """
    Generates qrels from the given instances.
    Args:
        instances: erd.ml.CERInstances
        file_name: name of output file
    """
    unique_entries = set()  # to keep unique entries for query_id + entity_id
    out = ""
    for ins in instances.get_all():
        if ins.target == "1":
            entry = (ins.q_id, ins.freebase_id)
            if not entry in unique_entries:
                out += ins.q_id + "\t"
                out += "0\t"
                out += ins.freebase_id + "\t"
                out += ins.target + "\n"
                unique_entries.add(entry)
    out_file = open(file_name, 'w')
    out_file.write(out)
    print "Qrel file is written to " + file_name


def read_args():
    """ Parses input arguments and returns parsed arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument("-gt", help="Generates ground truth instances", action="store_true", default=False)
    parser.add_argument("-qrel", help="Generates qrel", action="store_true", default=False)
    parser.add_argument("-qrelsets", help="Generates qrel for sets", action="store_true", default=False)
    parser.add_argument("-data", help="Data set name", choices=['ysqle', 'ysqle-erd', 'erd', 'toy'])

    args = parser.parse_args()

    # set default values
    if args.data is None:
        args.data = "ysqle-erd"

    return args


def take_action(args):
    if args.data == "erd":
        erd_gt.main(args)
    elif args.data == "ysqle":
        ysqle_gt.main(args)
    elif args.data == "ysqle-erd":
        ysqle_erd_gt.main(args)
    elif args.data == "toy":
        ysqle_erd_gt.main(args)

    if args.qrel:
        gt_inss = CERInstances.from_json(econfig.RES_DIR + "/" + args.data + "-gt.json")
        gen_qrel(gt_inss, econfig.DATA_DIR + "/qrel_" + args.data + ".txt")
    # elif args.qrelsets:
    #     gt_inss = CERInstances.from_json(econfig.RES_DIR + "/" + args.data + "-gt.json")
    #     gen_qrel_sets(gt_inss, econfig.DATA_DIR + "/qrel_sets_" + args.data + ".txt")


if __name__ == '__main__':
    take_action(read_args())