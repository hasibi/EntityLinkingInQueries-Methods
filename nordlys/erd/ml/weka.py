"""
Tools for Weka.
@author: Faegheh Hasibi
"""

import subprocess
import sys
from nordlys.erd import econfig
from nordlys import config


WEKA_JAR = config.LIB_DIR + "/weka.jar"
WEKA_CMD = ["java", "-Xmx1024m", "-cp", WEKA_JAR]


def interact_weka(parameters):
    """
    Interact with Weka.
    Args:
        parameters: List of parameteres. For example:
            ["-weka.classifiers.rules.ZeroR, "-t", "file"]
    """
    command = WEKA_CMD + parameters
    subprocess.call(command)


def train(train_set, model_file, classifier, classifier_params=None, folds=None):
    """
    Train rankLib instances and write the model into a file.
    Args:
        train_set: file name.
        model_file: File name for saving model.
        classifier: Weka classifier
        classifier_params: List of parameteres used for ranking algorithm.
        cv: Number of folds for cross validation
    """
    command = WEKA_CMD
    if classifier_params is not None:
        command += classifier_params
    command += [classifier, "-t", train_set, "-d", model_file]
    if folds is not None:
        command += ["-x", folds]
    print "Learning ..."
    k = model_file.rfind(".")
    subprocess.call(' '.join(command) + " > " + model_file[:k] + ".out", shell=True)
    out_file = open(model_file[:k] + ".out")
    print out_file.read()


def predict(test_set, model_file, classifier, score_file=None):
    """
    Predict score for a test set, given a model.
    Args:
        classifier: The classifier of the saved model.
        model_file: File name of previously saved model.
        test_set: File name.
        score_file: File for storing classifier's prediction.
    """
    print "Testing dataset " + test_set + "..."
    command = WEKA_CMD + [classifier, "-l", model_file, "-T", test_set]
    if score_file is not None:
        command += ["-p", "1"]
        print "Writing prediction in " + score_file + " ..."
        subprocess.call(' '.join(command) + " > " + score_file, shell=True)
    else:
        subprocess.call(command)


def main(argv):
    # Training and testing with weka
    logistic = "weka.classifiers.functions.Logistic"
    if argv[0] == "--train":
        train(argv[1], econfig.OUTPUT_DIR + "/test.model", logistic)
    elif argv[0] == "--test":
        predict(argv[1], econfig.OUTPUT_DIR + "/test.model", logistic, econfig.OUTPUT_DIR + "/score.txt")


if __name__ == '__main__':
    main(sys.argv[1:])
