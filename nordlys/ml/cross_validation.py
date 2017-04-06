"""
Cross-validation

We assume that instances (i) are uniquely identified by an instance ID and (ii) they have id and score properties.
We access them using the Instances class.

@author: Krisztian Balog
"""

import os
import json
from random import shuffle

from nordlys.ml.instances import Instances


class CrossValidation(object):
    """
    Class attributes:
        fold: dict of folds (1..k) with a dict
              {'training': [list of instance_ids]}, {'testing': [list of instance_ids]}

    """

    def __init__(self, k, instances, callback_train, callback_test):
        """
        :param k: number of folds
        :param instances: Instances object
        :param callback_train: Callback function for training model
        :param callback_test: Callback function for applying model
        """
        self.k = k
        self.folds = None
        self.instances = instances
        self.callback_train = callback_train
        self.callback_test = callback_test

    def create_folds(self, group_by=None):
        """Creates folds for the data set.

        :param group_by: property to group by (instance_id by default)
        """
        if group_by is not None:
            # instances are grouped by the value of a given property
            inss_dict = self.instances.group_by_property(group_by)
        else:
            # each instance is a group on its own
            inss_dict = {}
            for l in self.instances.get_all_ids():
                inss_dict[l] = [l]

        # shuffling
        inss_keys = inss_dict.keys()
        shuffle(inss_keys)

        # determines the number of folds
        num_folds = len(inss_keys) if self.k == -1 else self.k

        # creates folds
        self.folds = {}
        for f in range(num_folds):
            print "Generating fold " + str(f+1) + "/" + str(num_folds)
            fold = {'training': [], 'testing': []}
            for i, key in enumerate(inss_keys):
                w = "testing" if i % num_folds == f else "training"
                if group_by is not None:
                    fold[w] += inss_dict[key]
                else:
                    fold[w].append(self.instances.get(key).id)
            self.folds[f] = fold

    def get_instances(self, i, mode):
        """Returns instances from the given fold i \in [0..k-1].

        :param i: fold number
        :param mode: training or testing
        :return Instances object
        """
        inss = Instances()
        for l in self.folds[i][mode]:
            inss.add_instance(self.instances.get_instance(l))
        return inss

    def get_folds(self, filename=None, group_by=None):
        """Loads folds from file or generates them if the file doesn't exist.

        :param filename:
        :param k: number of folds
        :return:
        """
        if os.path.isfile(filename):
            self.load_folds(filename)
        else:
            self.create_folds(group_by)
            self.save_folds(filename)

    def save_folds(self, filename):
        """Saves folds to (JSON) file."""
        with open(filename, 'w') as outfile:
            json.dump(self.folds, outfile, indent=4)

    def load_folds(self, filename):
        """Loads previously created folds from (JSON) file."""
        json_data = open(filename)
        self.folds = json.load(json_data)
        if len(self.folds) != self.k:
            raise Exception("Error in splits file: number of folds mismatches!")

    def run(self):
        """Runs cross-validation."""

        # if folds haven't been initialized/created before (w/ get_folds or create_folds)
        # then they'll be created using the default grouping (i.e., based on instance_id)
        if self.folds is None:
            self.create_folds()

        # this holds the estimated target values (and also the confidence score, if available)
        test_inss = Instances()
        
        for i, fold in enumerate(self.folds):
            print "======================================="
            print "Cross validation for fold " + str(i) + " ..."
            model = self.callback_train(self.get_instances(fold, "training"))
            fold_test_inss = self.callback_test(self.get_instances(fold, "testing"), model)
            test_inss.append_instances(fold_test_inss.get_all())

        return test_inss

def main():

    #cv = CrossValidation(None, train_func, test_func)

    #cv.create_folds(10)
    #cv.save_folds("data/cv/splits.json")
    #cv.run()
    pass


if __name__ == "__main__":
    main()
