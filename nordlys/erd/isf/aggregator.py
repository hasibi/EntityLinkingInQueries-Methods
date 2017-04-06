"""
Aggregates entity based features.

@author: Faegheh Hasibi
"""

import numpy
from operator import mul


class Aggregator(object):
    """
    Class to aggregate features of and ISF instance
    Attribute: isf_ins: erd.ml.ISFInstance

    """
    def __init__(self, isf_ins=None):
        self.isf_ins = isf_ins

    def aggregate(self, ftrs, ftr_name):
        """
        aggregates feature ftrs for all entities in the iset.
        - Aggregation: Min, Max, Avg,

        Args:
            ftrs: Dictionary {en_id:feature, ...}
            ftr_name: Feature name; the name will be added to the aggregation method

        Returns:
            Aggregated features in form of {feature_name: feature, ...}
        """
        agg_ftrs = dict()
        agg_ftrs[ftr_name + '_min'] = min(ftrs.values())
        agg_ftrs[ftr_name + '_max'] = max(ftrs.values())
        # agg_ftrs[ftr_name + '_sum'] = sum(ftrs.values())
        # agg_ftrs[ftr_name + '_mul'] = reduce(mul, ftrs.values())
        agg_ftrs[ftr_name + '_avg'] = numpy.average(ftrs.values())
        # agg_ftrs[ftr_name + '_median'] = numpy.median(ftrs.values())
        # if self.isf_ins is not None:
        # agg_ftrs[ftr_name + '_wsum_men'] = self.wsum_men(ftrs)
        # agg_ftrs[ftr_name + '_wsum_men_pow'] = self.wsum_men_pow(ftrs)
        # agg_ftrs[ftr_name + '_wsum_set_men'] = self.wsum_set_men(ftrs)
        # agg_ftrs[ftr_name + '_wsum_set_men_pow'] = self.wsum_set_men_pow(ftrs)
        return agg_ftrs

    def wsum_men(self, ftrs):
        """
        Calculates weighted sum of features:
            score = sum(feature_i * |mention|)
        Args:
            ftrs: {en_id: feature, ...}
        """
        wsum = 0
        for en_id, feature in ftrs.iteritems():
            mention_len = len(self.isf_ins.inter_set[en_id].split())
            wsum += mention_len * feature
        return wsum

    def wsum_men_pow(self, ftrs):
        """
        Calculates weighted sum of features:
            score = sum(feature_i * (|mention| ^ |mention|))
        Args:
            ftrs: {en_id: feature, ...}
        """
        wsum = 0
        for en_id, feature in ftrs.iteritems():
            mention_len = len(self.isf_ins.inter_set[en_id].split())
            wsum += (mention_len ** mention_len) * feature
        return wsum

    def wsum_set_men(self, ftrs):
        """
        Calculates weighted sum of features:
            score = |all_mentions| * sum (feature_i )
            |all_mentions|: number of words in all mentions of the set.

        Args:
            ftrs: {en_id: feature, ...}
        """
        feature_sum = 0
        all_mentions_len = 0
        for en_id, feature in ftrs.iteritems():
            all_mentions_len += len(self.isf_ins.inter_set[en_id].split())
            feature_sum += feature
        return all_mentions_len * feature_sum

    def wsum_set_men_pow(self, ftrs):
        """
        Calculates weighted sum of features:
            score = (|all_mentions| ^ |all_mentions|) * sum(feature_i )
            |all_mentions|: number of words in all mentions of the set.

        Args:
            ftrs: {en_id: feature, ...}
        """
        feature_sum = 0
        all_mentions_len = 0
        for en_id, feature in ftrs.iteritems():
            all_mentions_len += len(self.isf_ins.inter_set[en_id].split())
            feature_sum += feature
        return (all_mentions_len ** all_mentions_len) * feature_sum