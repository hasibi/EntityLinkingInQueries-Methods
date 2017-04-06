"""
Generates train set for Interpretation Set Finding (ISF).
The core method to generate the train set is "gen_train".

@author: Faegheh Hasibi

"""
from nordlys.erd import econfig
from nordlys.erd.isf.set_generator import SetGen
from nordlys.erd.isf.set_detector import SetDetect
from nordlys.erd.ml.cer_instances import CERInstances
from nordlys.erd.ml.isf_instances import ISFInstances, ISFInstance


def gen_train_set(gt_inss, cer_train_inss, k):
    """
    Generates ISF train set.
    process:
        1. Converts ground-truth instances to ISF instances
        2. Convert all CER train instances to ISF instances (No K is considered)
        3. Check the generated ISF instances( from CER train) with groundtruth:
            - if it can be found in gt, change its label
            - Otherwise, check if its rank less than K. If yes add it to the train set.

    Args:
        gt_inss: erd.ml.CERInss, CER instances of groundtruth.
        cer_inss: erd.ml.CERInss, all CER instances from CER phase.
        k: Top-K entities for each query
    Return:
        erd.ml.ISFInstances
    """
    print "Generating ISF train set ..."
    # Converts ground-truth instances to ISF instances
    gt_isf_inss = gt_to_isf_inss(gt_inss)

    gt_isf_inss_by_query = gt_isf_inss.group_by_query()
    cer_train_inss_by_query = cer_train_inss.group_by_query()

    train_set_list = []
    for qid, inss_list in cer_train_inss_by_query.iteritems():

        print "Query [" + qid + "]"
        # Generate ISF instances form ranked CER instances
        if qid == "trec-2013-129_1":
        # this is a long query with no positive entity. Here we just fasten the process, nothing diff from other queries
            set_generator = SetGen(CERInstances(inss_list), k)
        else:
            # No K is defined, all instances are converted
            set_generator = SetGen(CERInstances(inss_list))
        all_isf_inss = set_generator.gen_isf_inss()

        # Merges all instances (positive from gt_inss and negatives from cer_inss)
        query_train_set = merge_inss(ISFInstances(gt_isf_inss_by_query[qid]), all_isf_inss, k)
        train_set_list.append(query_train_set)
    return ISFInstances.concatenate_inss(train_set_list)


def gen_cv_set(gt_inss, cer_cv_inss, k):
    """
    Generates ISF train set.
    process:
        1. Convert all CER CV instances to ISF instances
        2. Changes the label of instances that are in the groundtruth

    Args:
        gt_inss: erd.ml.CERInss, CER instances of groundtruth.
        cer_cv_inss: erd.ml.CERInss, ranked CER CV instances from CER phase.
        k: Top-K entities for each query
    Return:
        erd.ml.ISFInstances
    """
    print "\nGenerating ISF cross-validation set ..."
    # Generate ISF instances form ranked CER instances
    set_generator = SetGen(cer_cv_inss, k)
    cv_inss = set_generator.gen_isf_inss()

    # Converts ground-truth instances to ISF instances
    gt_isf_inss = gt_to_isf_inss(gt_inss)
    gt_inss_dict = gt_isf_inss.group_by_query()

    # change label of instances that are in the groundtruth
    for isf_ins in cv_inss.get_all():
        found_ins = __find_ins_in_gt(isf_ins, gt_inss_dict[isf_ins.q_id])
        if found_ins is not None:
            isf_ins.target = found_ins.target
    return cv_inss


def gt_to_isf_inss(gt_inss):
    """
    Converts Groundtruth instances to ISF instances.
    Args:
        gt_inss: erd.ml.CERInstances, CER instances of groundtruth
    Returns:
        erd.ml.ISFInstances
    """
    # print "Converting ground truth instances to ISF instances ..."
    inss_by_query = gt_inss.group_by_query()
    isf_inss = ISFInstances()
    ins_id = 0
    for q_id, inss_list in inss_by_query.iteritems():
        q_content = inss_list[0].q_content

        # Gets the number of interpretation sets for each query
        iset_ids = set([ins.set_id for ins in inss_list])

        # Generates ISF instance for each interpretation set id
        for iset_id in iset_ids:
            iset = dict()
            # Generates interpretation set for the current set id
            for ins in inss_list:
                if (ins.set_id == iset_id) and (iset_id != "-1"):
                    iset[ins.en_id] = ins.mention
            # Generates an ISF instance
            if len(iset) > 0:
                isf_ins = ISFInstance(ins_id)
                isf_ins.target = "1"
                isf_ins.inter_set = iset
                isf_ins.q_id, isf_ins.q_content = q_id, q_content
                isf_inss.add_instance(isf_ins)
                ins_id += 1
    return isf_inss


def merge_inss(gt_isf_inss, cand_isf_inss, k):
    """
    Merges ISF instances of groundtruth and the other ISF instances.

    Args:
        gt_isf_inss:  Groundtruth instances for interpretation sets.
        all_isf_inss: All other ISF instances (all possible interpretations of the query.
    Return:
        erd.ml.ISFInstances, train set instances
    """
    train_inss = ISFInstances()

    # groups instances by query
    gt_inss_dict = gt_isf_inss.group_by_query()
    cand_inss_dict = cand_isf_inss.group_by_query()

    # merges instances:
    # Takes all ranked CER instances and set label "1" to the ones that are in the gt
    # it is guaranteed that all ranked CER instances should have an entry in groundtruth.
    ins_id = 0
    for q_id, inss_list in cand_inss_dict.iteritems():
        for cand_ins in inss_list:
            gt_ins = __find_ins_in_gt(cand_ins, gt_inss_dict[q_id])
            # change label of instances that are in the groundtruth
            if gt_ins is not None:
                cand_ins.target = gt_ins.target
            # ignore the instance
            elif not __in_top_k(cand_ins, k):
                continue
            cand_ins.id = ins_id
            train_inss.add_instance(cand_ins)
            ins_id += 1
        # # If there is a conflict between
        # if len(found_inss) != len(gt_inss_dict[q_id]):
        #     print "NOTE: Gt instances that are not found among CER train instances."
        #     print q_id
        #     print "found instances:"
        #     for f_ins in found_inss:
        #         print f_ins.inter_set
        #     print "gt instances:"
        #     for g_ins in gt_inss_dict[q_id]:
        #         print g_ins.inter_set
        #     print "-----------------------------------"
    return train_inss


def __find_ins_in_gt(isf_ins, gt_ins_list):
    """
    Checks whether an instance can be found in given list of gt-instances or not.
    Args:
        isf_ins: ISF instance
        gt_ins_list: [isf_ins, ...], List of ISF instances
    Returns:
        boolean
    """
    found = None
    ins_iset = set([(en, men) for en, men in isf_ins.inter_set.iteritems()])
    for gt_ins in gt_ins_list:
        # check both entities and their mentions
        gt_iset = set([(en, men) for en, men in gt_ins.inter_set.iteritems()])
        if ins_iset == gt_iset:
            found = gt_ins
            break
    return found


def __in_top_k(isf_ins, k):
    """ Checks whether the entities of among top-k entities. """
    in_top_k = True
    for cer_atts in isf_ins.cer_atts.values():
        if cer_atts['rank'] > k:
            in_top_k = False
    return in_top_k


def main(args):
    """
    Generates ISF train set
    Required Args: -isf -d <data_name> -in <CER_instance_file> -k <integer> [-nof]
    """
    if args.addfeat:
        train_inss = ISFInstances.from_json(args.input)
        SetDetect.add_features(train_inss)
         # Writes ISF train set into files
        file_name = args.input[:args.input.rfind("-nof")]
        train_inss.to_json(file_name + ".json")
        # train_inss.to_str(file_name + "-qi.txt")
        return


    # Loads instances from CER phase, Should be ranked CER instances
    cer_inss = CERInstances.from_json(args.input)

    # Loads groundtruth
    gt_json = econfig.RES_DIR + "/" + args.data + "-gt.json"
    gt_inss = CERInstances.from_json(gt_json)

     # Generates train set
    if args.trainset:
        # Generates instances of train set and adds features
        train_inss = gen_train_set(gt_inss, cer_inss, args.k)
        print "Number of ISF train instances:", len(train_inss.get_all())
        if not args.nofeatures:
            SetDetect.add_features(train_inss)

        # Writes ISF train set into files
        file_name = args.input[:args.input.rfind(".json")] + "-isfTrain-k" + str(args.k)
        if args.nofeatures:
            file_name += "-nof"
        train_inss.to_json(file_name + ".json")
        train_inss.to_str(file_name + ".txt")

    # generates CV set
    elif args.cvset:
        cv_inss = gen_cv_set(gt_inss, cer_inss, args.k)
        if not args.nofeatures:
            SetDetect.add_features(cv_inss)
        file_name = args.input[:args.input.rfind(".json")] + "-isfCV-k" + str(args.k)
        if args.nofeatures:
            file_name += "-nof"
        cv_inss.to_json(file_name + ".json")  #"-qi.json")
        # cv_inss.to_str(file_name + ".txt")  #"-qi.txt")



