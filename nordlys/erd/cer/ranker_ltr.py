"""
Uses Learning to Rank  to rank entities
@author: Faegheh Hasibi
"""
from datetime import datetime
import pickle


from nordlys.erd.features.query_sim_feat import QuerySimFeat
from nordlys.ml.cross_validation import CrossValidation
from nordlys.erd.features.entity_feat import EntityFeat
from nordlys.erd.features.mention_feat import MentionFeat
from nordlys.erd.features.entity_mention_feat import EntityMentionFeat
from nordlys.erd import econfig
from nordlys.erd.groundtruth import erd_gt, ysqle_erd_gt, ysqle_gt
from nordlys.erd.query.query import Query
from nordlys.erd.ml.cer_instances import CERInstances, CERInstance
from nordlys.ml.ml import ML
from nordlys.retrieval.lucene_tools import Lucene


class RankerLTR(object):
    """
    Attributes:
        tree: int, Number of trees
        depth: int, depth of the trees
        alpha: float, learning rate
        model: the trained model
    """
    def __init__(self, commonness_th=None, sf_source=None, filter=True, model=None, config={}):
        self.commonness_th = commonness_th
        self.sf_source = sf_source
        self.filter = filter
        self.config = config
        self.model = model
        self.ml = ML(config) #if config is not None else None

    def train(self, inss, model_file=None, feat_imp_file=None):
        """
        Trains a model and saves it to a file.
        - This function currently only supports GBRT.

        Args:
            inss: erd.ml.CERInstances, train instances
            model_file: A file to save the model. For None value, the model will not be saved

        Returns:
            ranker, the learned model
        """
        config = self.config
        if model_file is not None:
            config['save_model'] = model_file
        if feat_imp_file is not None:
            config['save_feature_imp'] = feat_imp_file
        self.ml.config = config
        ranker = self.ml.train_model(inss)
        return ranker

    def cross_validate(self, inss, num_folds, folds_name=None, gen_folds=False):
        """
        Performs k-fold cross validation.

        :param inss: erd.ml.CERInstances
        :param num_folds: int, number of folds
        :param folds_name: file name for saving the folds. It adds a postfix to the file name.
                e.g. "./output/res/erd-ltr" -> "./output/res/erd-ltr-f1-train.json"

        :return All of instances ranked by cross validation
        """
        kcv = CrossValidation(num_folds, inss, self.train, self.rank_inss)

        # loads/generates folds
        if gen_folds:
            kcv.create_folds(group_by="session")
            if folds_name is not None:
                kcv.save_folds(folds_name)
        else:
            kcv.load_folds(folds_name)

        # Cross validation
        inss = kcv.run()
        inss.__class__ = CERInstances
        for ins in inss.get_all():
            ins.__class__ = CERInstance
        return inss

    def rank_inss(self, inss, model=None):
        """
        Ranks the instances using the given trained model.

        :param inss: erd.ml.CERInstances

        :return erd.ml.CERInstances, ranked instances
        """
        if model is None:  # Done for CV call_back_test method
            model = self.model
        return self.ml.apply_model(inss, model)

    def rank_queries(self, queries, time_log_file=None):  # commonness_th, filter=True,
        """
        Ranks entities for the given queries using the trained model.

        :param queries: a dictionary, {q_id: q_content, ...}
        :param time_log_file: file name to save time log
        :return erd.ml.CERInstances, Ranked instances
        """
        print "Ranking queries ..."
        total_time = 0.0
        s_t = datetime.now()  # start time
        inss_list = []  # list of Instances

        # Ranks queries
        for q_id, q_content in queries.iteritems():
            query = Query(q_id, q_content)
            q_inss = self.rank_query(query)
            if len(q_inss.get_all()) == 0:
                print "==================================================="
                print "No candidate entity for query " + q_id + ", " + q_content
                print "==================================================="
            inss_list.append(q_inss)

        # time log
        e_t = datetime.now()
        diff = e_t - s_t
        total_time += diff.total_seconds()
        time_log = "Execution time(min):\t" + str(round(total_time/60, 4)) + "\n"
        time_log += "Avg. time per query:\t" + str(round(total_time/len(queries), 4)) + "\n"
        print time_log
        # open(time_log_file + ".timelog", "w").write(time_log)
        # print "Time log:\t" + time_log_file + ".timelog"
        return CERInstances.concatenate_inss(inss_list)

    def rank_query(self, query):
        """
        Generates ranking score for entities related to the given query.

        :param query: query.Query
        :return erd.ml.CERInstances
        """
        q_inss = CERInstances.gen_instances(query, self.commonness_th, sf_source=self.sf_source, filter=self.filter)
        RankerLTR.add_features(q_inss, self.commonness_th, self.sf_source)
        self.rank_inss(q_inss)
        return q_inss

    @staticmethod
    def add_features(inss, commonness_th, sf_source):
        print "Extracting features ..."
        i = 0
        for ins in inss.get_all():
            ins.features = RankerLTR.get_features(ins, commonness_th, sf_source)
            i += 1
            if i % 1000.0 == 0:
                print "Features are generated until instance " + str(ins.id)
        return inss

    @staticmethod
    def get_features(ins, commonness_th, sf_source):
        """
        Concatenate all features.

        :param ins: ml.Instance
        """
        all_ftrs = {}
        # --- mention features ---
        mention_ftr = MentionFeat(ins.mention, sf_source)
        all_ftrs['len'] = mention_ftr.mention_len()
        all_ftrs['ntem'] = mention_ftr.ntem()
        all_ftrs['smil'] = mention_ftr.smil()
        all_ftrs['matches'] = ins.matches if ins.matches is not None else mention_ftr.matches(commonness_th)
        all_ftrs['len_ratio'] = mention_ftr.len_ratio(Query.preprocess(ins.q_content))
        # --- entity features ---
        en_ftr = EntityFeat(ins.en_id)
        all_ftrs['redirects'] = en_ftr.redirects()
        all_ftrs['links'] = en_ftr.links()
        # --- entity-mention features ---
        en_mention_ftr = EntityMentionFeat(ins.en_id, ins.mention)
        all_ftrs['commonness'] = ins.commonness
        all_ftrs['mct'] = en_mention_ftr.mct()
        all_ftrs['tcm'] = en_mention_ftr.tcm()
        all_ftrs['tem'] = en_mention_ftr.tem()
        all_ftrs['pos1'] = en_mention_ftr.pos1()
        all_ftrs.update(RankerLTR.__lm_scores(ins.en_id, ins.mention, "m"))
        # --- entity-query features ---
        en_query_ftr = EntityMentionFeat(ins.en_id, ins.q_content)
        all_ftrs['qct'] = en_query_ftr.mct()
        all_ftrs['tcq'] = en_query_ftr.tcm()
        all_ftrs['teq'] = en_query_ftr.tem()
        mlm_tc = QuerySimFeat(ins.q_content).nllr_mlm_score(ins.en_id, {'names': 0.2, 'contents': 0.8})  # mlm_score
        all_ftrs['mlm-tc'] = mlm_tc if mlm_tc is not None else 0
        all_ftrs.update(RankerLTR.__lm_scores(ins.en_id, ins.q_content, "q"))
        return all_ftrs

    @staticmethod
    def __lm_scores(en_id, txt, prefix):
        """ Calculates all LM scores. """
        feat_field_dict = {'title': econfig.TITLE, 'sAbs': econfig.SHORT_ABS, 'lAbs': econfig.LONG_ABS,
                           'links': econfig.WIKILINKS, 'cats': econfig.CATEGORIES, 'catchall': Lucene.FIELDNAME_CONTENTS}
        ftr_extractor = QuerySimFeat(txt)
        scores = dict()
        for feature_name, field in feat_field_dict.iteritems():
            lm_score = ftr_extractor.nllr_lm_score(en_id, field)  # lm_score(en_id, field)
            scores[prefix + feature_name] = lm_score if lm_score is not None else 0
        return scores


def main(args):
    """
    Required args for training:         -train -cer -t <int> -l <int> -in <train_set_name.json>
    Required args for cross validation: -cv -cer -d <data_name> -c <commonness> -t <int> -l <int>
    Required args for ranking:          -rank -ltr -m <model_file>
    Valid args for ranking:             -d <data_name> -qid <str> -query <str> -c <commonness>
    """
    settings_str = "-ltr-t" + str(args.tree)
    model_name = ""
    if args.depth is not None:
        settings_str += "-d" + str(args.depth)
        model_name = "gbrt"
    elif args.maxfeat is not None:
        settings_str += "-m" + str(args.maxfeat)
        model_name = "rf"

    ml_config = {'model': model_name,
                 'parameters': {'tree': args.tree, 'depth': args.depth, 'maxfeat': args.maxfeat}}

    # ==== Train ====
    if args.train:
        train_inss = CERInstances.from_json(args.input)
        file_name = args.input[:args.input.rfind(".json")] + settings_str
        ranker_ltr = RankerLTR(config=ml_config)  # model_name, tree=args.tree, depth=args.depth, max_features=args.maxfeat)
        ranker_ltr.train(train_inss, model_file=file_name + ".model", feat_imp_file=file_name + "-feat_imp.txt")

    # ==== Cross Validation ====
    elif args.cv:
        in_file_name = args.input[:args.input.rfind(".json")]
        cv_inss = CERInstances.from_json(args.input)
        ranker_ltr = RankerLTR(config=ml_config) # model_name, tree=args.tree, depth=args.depth, max_features=args.maxfeat)
        ranked_inss = ranker_ltr.cross_validate(cv_inss, args.folds,
                                                folds_name=in_file_name + "-" + str(args.folds) + "f-folds.json",
                                                gen_folds=args.genfolds)

        ranked_inss.to_json(in_file_name + "-" + str(args.folds) + "f" + settings_str + ".json")
        ranked_inss.to_str(in_file_name + "-" + str(args.folds) + "f" + settings_str + ".txt")
        use_dbp = True if args.data == "ysqle" else False
        ranked_inss.to_treceval(settings_str, in_file_name + "-" + str(args.folds) + "f" + settings_str + ".treceval", use_dbp)

    # ==== Rank ====
    elif args.rank:
        # loads model
        model = pickle.loads(open(args.model, 'r').read())
        ranker_ltr = RankerLTR(model=model, commonness_th=args.commonness, sf_source=args.sfsource, filter=args.filter)
        settings_str = "-ltr"
        if args.model.rfind("-d") != -1:
            settings_str += args.model[args.model.rfind("-t"):args.model.rfind("-d")]
            settings_str += args.model[args.model.rfind("-d"):args.model.rfind(".model")]
        elif args.model.rfind("-m") != -1:
            settings_str += args.model[args.model.rfind("-t"):args.model.rfind("-m")]
            settings_str += args.model[args.model.rfind("-m"):args.model.rfind(".model")]

        # Ranks instances
        if args.input is not None:
            inss = CERInstances.from_json(args.input)
            ranked_inss = ranker_ltr.rank_inss(inss)
            # Writes instances
            file_name = args.input[:args.input.rfind(".json")] + settings_str
            ranked_inss.to_json(file_name + ".json")
            ranked_inss.to_str(file_name + ".txt")
            ranked_inss.to_treceval(file_name, file_name + ".treceval")

        # Ranks queries
        else:
            if args.query is not None:
                queries = [Query(args.qid, args.query)]
            elif args.data == "erd":
                queries = erd_gt.read_queries()
            elif args.data == "ysqle-erd":
                queries = ysqle_erd_gt.read_queries()
            elif args.data == "toy":
                queries = ysqle_erd_gt.read_queries(ysqle_erd_file=econfig.DATA_DIR + "/toy.tsv")

            # rank the query instances
            filter_str = "" if args.filter else "-unfilter"
            # sf_source_str = "-" + args.sfsource if args.sfsource is not None else ""
            file_name = econfig.EVAL_DIR + "/" + args.data + "-c" + str(args.commonness) + settings_str + filter_str
            ranked_inss = ranker_ltr.rank_queries(queries, time_log_file=file_name)
            ranked_inss.to_json(file_name + ".json")
            # ranked_inss.to_str(file_name + ".txt")
            run_id = file_name[file_name.rfind("/")+1:]
            ranked_inss.to_treceval(run_id, file_name + ".treceval")
