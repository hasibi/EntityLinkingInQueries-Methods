"""
This is the main entry point for command line usage of cer package.

Functionality:
- Ranks entities using MLM and LTR approach
- For LTR approach, performs training GBRT model and cross validation
- Performs cross validation for LTR method

Accepts input in three formats:
- Single query
- Queries of dataset (erd, ysqle, ysqle-erd)
- List of CER instances

See the detailed description at [wiki/cer] (https://bitbucket.org/kbalog/nordlys-erd/wiki/cer)

@author: Faegheh Hasibi
"""

import argparse
from nordlys.erd.cer import ranker_mlm, ranker_ltr


def read_args():
    """ Parses input arguments and returns parsed arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument("-rank", help="Rank entities", action="store_true", default=False)
    parser.add_argument("-data", help="Data set name", choices=['ysqle', 'ysqle-erd', 'erd', 'toy'])
    parser.add_argument("-c", "--commonness", help="Commonness threshold", type=float)
    parser.add_argument("-qid", help="Query id", type=str)
    parser.add_argument("-query", help="query text", type=str)
    parser.add_argument("-in", "--input", help="Input file from previous step", type=str)
    parser.add_argument("-unf", "--filter", help="Do not perform filtering", action="store_false", default=True)
    parser.add_argument("-sfs", "--sfsource", help="Surface form sources", choices=['facc', 'wiki'])

    # mlm parameters
    parser.add_argument("-mlm", help="MLM method for entity ranking", action="store_true", default=False)
    parser.add_argument("-cmn", help="MLM-cmn method for entity ranking", action="store_true", default=False)
    parser.add_argument("-weights", help="MLM weights", type=str)

    # ltr parameters
    parser.add_argument("-ltr", help="LTR method for entity ranking", action="store_true", default=False)
    parser.add_argument("-model", help="Trained model file", type=str)
    parser.add_argument("-tree", help="Number of trees", type=int)
    parser.add_argument("-depth", help="Depth of tress (used for GBRT)", type=int)
    parser.add_argument("-maxfeat", help="Max features (used for RF)", type=int)
    parser.add_argument("-train", help="Train a model", action="store_true", default=False)
    parser.add_argument("-cv", help="Cross validation for the given instances", action="store_true", default=False)
    parser.add_argument("-f", "--folds", help="Number of folds", type=int)
    parser.add_argument("-genfolds", help="Cross validation for the given instances", action="store_true", default=False)

    args = parser.parse_args()

    # set default values
    if args.data is None:
        args.data = "ysqle-erd"
    if args.tree is None:
        args.tree = 1000

    return args


def take_action(args):
    if args.mlm:
        ranker_mlm.main(args)
    elif args.ltr:
        ranker_ltr.main(args)

        

if __name__ == '__main__':
    take_action(read_args())