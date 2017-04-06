"""
Methods for query segmentation and interpretations:
 - Generates segmentation of a query for the given mentions
 - Generates interpretation sets for a query segmentation
 - Generates all interpretation sets of a query

@author: Faegheh Hasibi
"""


from itertools import combinations


def segment(query, mentions):
    """
    Performs query segmentation.
    Each segmentation of the query is a set of non-overlapping mentions.

    :param query: erd.query.Query
            * E.g. Query("yahoo-111_1", "jon gruden rumors")
    :param mentions: list of mentions
            * E.g. ['jon gruden', 'gruden', 'rumors', 'jon']
    :return list of query segmentations
            * E.g:
            [(u'jon gruden',), (u'gruden',), (u'rumors',), (u'jon',),
            (u'jon gruden', u'rumors'), (u'gruden', u'rumors'), (u'gruden',
            u'jon'), (u'rumors', u'jon'), (u'gruden', u'rumors', u'jon')]
    """
    # Generates subset of entity mentions, with length less than query
    sub_sets = []
    for i in xrange(1, len(query.content.split())+1):
        sub_sets += list(combinations(mentions, i))
    # Deletes the sets with overlapping mentions.
    segments = []
    for mention_set in sub_sets:
        if not is_overlapping(mention_set):
            segments.append(mention_set)
    return segments


def segment_to_iset(segmentation, men_en_dict):
    """
    Generates all candidate interpretation sets for the given segmentation.

    :param segmentation: a set of non-overlapping mentions
            * E.g. (u'gruden', u'jon')

    :param men_en_dict: {mention: en}
            * E.g. {u'gruden': [u'<dbpedia:Jon_Gruden>'],
                   u'jon': [u'<dbpedia:Jon_(film)>', u'<dbpedia:Jon_Favreau>'] , ...}
    :return A list of interpretation sets
            * E.g. [{u'<dbpedia:Jon_Gruden>': u'gruden', u'<dbpedia:Jon_(film)>': u'jon'},
                {u'<dbpedia:Jon_Gruden>: u'gruden', u'<dbpedia:Jon_Favreau>': u'jon'}]
    """
    inter_sets = {}
    for mention in segmentation:
        # set(men_en_dict[mention]) should be set, otherwise redundant isets will be generated.
        inter_sets = __append_new_mention(inter_sets, mention, set(men_en_dict[mention]))
    return inter_sets


def gen_iset(query, mention_en_dict):
    """"
    Generates interpretation sets for the given query.

    :param query: erd.query.Query
    :param mention_en_dict: {mention: [en1, en2, ...]}
    :return A list of dictionaries, where each dict is like {men:en_id, ...}
            * E.g. [{'<dbpedia:Jon_Gruden>': 'jon gruden'},
            {'<dbpedia:Jon_Gruden>': 'gruden', '<dbpedia:Rumors>': 'rumors'},..]
    """
    segments = segment(query, mention_en_dict.keys())
    iset_q = []
    for seg in segments:
        iset_seg = segment_to_iset(seg, mention_en_dict)
        # check if all mentions of a segmentation are assigned an entity.
        # E.g.
        #   {tweets:[<dbpedia:Twitter>, <dbpedia:Breaking_Tweets>] twitter:[<dbpedia:Twitter>]}
        # All generated isets for (tweets, twitter) are:
        #   {u'<dbpedia:Twitter>': u'twitter', u'<dbpedia:Breaking_Tweets>': u'tweets'}
        #   {u'<dbpedia:Twitter>': u'twitter'}
        # But only the first one is valid. By this check we filter the second iset.
        seg_iset = []
        for iset in iset_seg:
            if len(iset) == len(seg):
                seg_iset.append(iset)
        iset_q += seg_iset
    return iset_q


def is_overlapping(mention_set):
    """
    Checks whether the strings of a set overlapping or not.
    i.e. if there exists a term that appears twice in the whole set.

    E.g. {"the", "music man"} is not overlapping
         {"the", "the man", "music"} is overlapping.

    NOTE: If a query is "yxxz" the mentions {"yx", "xz"} and {"yx", "x"} are overlapping.

    :param str_set: A set/list of strings
    :return True/False
    """
    word_list = []
    for mention in mention_set:
        word_list += set(mention.split())
    if len(word_list) == len(set(word_list)):
        return False
    else:
        return True

def __append_new_mention(inter_set_list, mention, entities):
    """
    Appends the entities of a new mention to the existing interpretation sets

    :param inter_set_list: a list of candidate interpretation sets.
            *E.g. [{<dbpedia:Man_(band)>: man}, {<dbpedia:MAN_SE>: man}]

    :param mention: string, the new mention that will be added to each set
            *E.g. "the"

    :param entities: List of entities linked to the mention
            *E.g.[<dbpedia:The_Belltower>, <dbpedia:Times_Higher_Education>]

    :return A new list of interpretation sets
            *E.g. [{<dbpedia:Man_(band)>:man, <dbpedia:The_Belltower>:the},
                   {<dbpedia:Man_(band)>:man,<dbpedia:Times_Higher_Education>:the},
                   {<dbpedia:MAN_SE>:man, <dbpedia:The_Belltower>:the},
                   {<dbpedia:MAN_SE>:man, <dbpedia:Times_Higher_Education>:the}]
    """
    new_inter_set_list = []
    # if the list is empty
    if (inter_set_list is None) or (len(inter_set_list) == 0):
        new_inter_set_list = [{x: mention} for x in entities]
        return new_inter_set_list
    # Appends each entity to the exiting lists and generate new sets.
    for en_id in entities:
        for inter_set in inter_set_list:
            inter_set_copy = inter_set.copy()
            inter_set_copy[en_id] = mention
            new_inter_set_list.append(inter_set_copy)
    return new_inter_set_list

