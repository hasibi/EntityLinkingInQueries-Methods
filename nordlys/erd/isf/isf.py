"""
This is the main entry point for command line usage of isf package.

Functionality:
- Converts CER instances to ISF instances (Set generation)
- Predicts interpretation sets
- Trains the interpretation set finding model (GBRT)

The input of the package can be:
- CER instances for set generation
- ISF instances for set detection

See the detailed description at [wiki/isf] (https://bitbucket.org/kbalog/nordlys-erd/wiki/isf)

@author: Faegheh Hasibi
"""

import argparse
from nordlys.erd.isf import set_generator, set_detector, greedy


def read_args():
    """ Parses input arguments and returns parsed arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument("-sg", "--setgen", help="Generate interpretation set", action="store_true", default=False)
    parser.add_argument("-train", help="Train a model", action="store_true", default=False)
    parser.add_argument("-predict", help="predict the label of instances", action="store_true", default=False)
    parser.add_argument("-model", help="Trained model file", type=str)
    parser.add_argument("-k", help="top-K entities to be considered from CER step", type=int)
    parser.add_argument("-tree", help="Number of trees", type=int)
    parser.add_argument("-depth", help="Depth of tress (used for GBRT)", type=int)
    parser.add_argument("-maxfeat", help="Max features (used for RF)", type=int)
    parser.add_argument("-in", "--input", help="Input file from previous step", type=str)
    parser.add_argument("-cv", help="Cross validation for the given instances", action="store_true", default=False)
    parser.add_argument("-f", "--folds", help="Number of folds", type=int)
    parser.add_argument("-genfolds", help="Cross validation for the given instances", action="store_true", default=False)

    parser.add_argument("-greedy", help="ISF using greedy approach", action="store_true", default=False)
    parser.add_argument("-top", help="ISF using top-ranked entity", action="store_true", default=False)
    parser.add_argument("-th", "--threshold", help="Score threshold for greedy approach", default=None, type=float)

    parser.add_argument("-generative", help="ISF using generative model", action="store_true", default=False)
    args = parser.parse_args()

    # set default values
    if args.tree is None:
        args.tree = 1000

    return args


def take_action(args):
    if args.setgen:
        set_generator.main(args)
    elif args.train or args.predict or args.cv:
        set_detector.main(args)
    elif args.greedy:
        greedy.main(args)
    # elif args.top:
    #     top_rank.main(args)
    # elif args.generative:
    #     greedy_tagme.main(args)
        

if __name__ == '__main__':
    take_action(read_args())