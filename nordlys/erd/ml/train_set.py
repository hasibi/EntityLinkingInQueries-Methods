"""
This is the main entry point for command line usage of ml package.

Functionality:
- Generates train set for CER and ISF step.

Data support:
- ERD dataset
- YSQLE
- YSQLE-erd

See the detailed description at [wiki/trainset] (https://bitbucket.org/kbalog/nordlys-erd/wiki/trainset)

@author: Faegheh Hasibi
"""

import argparse
from nordlys.erd.ml import train_set_cer, train_set_isf


def read_args():
    """ Parses input arguments and returns parsed arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument("-cer", help="Candidate Entity Finding", action="store_true", default=False)
    parser.add_argument("-isf", help="Interpretation Set Finding", action="store_true", default=False)
    parser.add_argument("-data", help="Data set name", choices=['ysqle', 'ysqle-erd', 'erd', 'toy'])
    parser.add_argument("-c", "--commonness", help="Commonness threshold", type=float)
    parser.add_argument("-k", help="top-K entities to be considered for ISF step", type=int)
    parser.add_argument("-in", "--input", help="Input file, instances from CER step", type=str)
    parser.add_argument("-nof", "--nofeatures", help="No features are generated", action="store_true", default=False)
    parser.add_argument("-af", "--addfeat", help="Adds features to the instances", action="store_true", default=False)
    parser.add_argument("-ts", "--trainset", help="Generate train set", action="store_true", default=False)
    parser.add_argument("-cvs", "--cvset", help="Generate CV set", action="store_true", default=False)
    parser.add_argument("-unf", "--filter", help="Do not perform filtering", action="store_false", default=True)
    parser.add_argument("-sfs", "--sfsource", help="Surface form sources", choices=['facc', 'wiki'])

    args = parser.parse_args()

    # set default values
    if args.data is None:
        args.data = "ysqle-erd"

    return args


def take_action(args):
    if args.cer:
        train_set_cer.main(args)
    elif args.isf:
        train_set_isf.main(args)
        

if __name__ == '__main__':
    take_action(read_args())