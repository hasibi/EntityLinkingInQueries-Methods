"""
All methods for pruning

@author: Faegheh Hasibi
"""

import operator
from nordlys.erd.ml.cer_instances import CERInstances


def prune_delta(query_inss):
    """ prunes entities bases on largest delta between ranking scores. """
    if len(query_inss.get_all()) <= 2:
        return query_inss

    ins_scores = []
    for ins in query_inss.get_all():
        if ins.score is not None:
            ins_scores.append((ins.id, ins.score))

    #sort
    sorted_inss = sorted(ins_scores, key=operator.itemgetter(1), reverse=True)

    # initiate max delta and valid instances
    tuple0, tuple1 = sorted_inss[0], sorted_inss[1]
    valid_inss = [query_inss.get_instance(tuple0[0])]
    max_delta = tuple0[1] - tuple1[1]

    for i in xrange(1, len(sorted_inss)):
        # if max_delta is not found, the last instances is also considered.
        if i == (len(sorted_inss) - 1):
            valid_inss.append(query_inss.get_instance(sorted_inss[i][0]))
            return CERInstances(valid_inss)

        # adds and instance if delta is the largest so far
        delta = sorted_inss[i][1] - sorted_inss[i + 1][1]
        if delta >= max_delta:
            valid_inss.append(query_inss.get_instance(sorted_inss[i][0]))
            max_delta = delta
        else:
            break
    return CERInstances(valid_inss)


def prune_top_k(inss, k=None):
    """
    Filters top-k entities for each query.
    Return all instances, if k is None.
    """
    if k is None:
        return inss

    inss.sort()
    valid_inss = CERInstances()
    for ins in inss.get_all():
        if ins.rank <= k:
            valid_inss.add_instance(ins)
    return valid_inss

def prune_threshold(query_inss, threshold):
    """ prunes based on a static threshold of ranking score."""
    valid_inss = []
    for ins in query_inss.get_all():
        if (ins.score is not None) and (ins.score > threshold):
            valid_inss.append(ins)
    return CERInstances(valid_inss)