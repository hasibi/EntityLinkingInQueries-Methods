"""
Generates candidate sets and their features.

@author: Faegheh Hasibi
"""

import pickle
from itertools import combinations

from nordlys.erd import econfig
from nordlys.erd.features.entity_feat import EntityFeat
from nordlys.erd.features.facc_feat import FACCFeat
from nordlys.erd.ml.isf_instances import ISFInstances, ISFInstance
from nordlys.erd.features.query_sim_feat import QuerySimFeat
from nordlys.erd.features.graph_feat import GraphFeat
from nordlys.erd.isf.aggregator import Aggregator
from nordlys.ml.cross_validation import CrossValidation
from nordlys.ml.ml import ML


class SetDetect(object):
    """
    Tools for interpretation set detection.
    Attributes:
        tree: number of trees
        depth: Depth of the trees
        classifier: trained classifier
    """

    def __init__(self, model_name=None, tree=None, depth=None, max_features=None, model=None):
        self.config = {'parameters': {}}
        if model_name is not None:
            self.config['model'] = model_name
        if tree is not None:
            self.config['parameters']['tree'] = tree
        if depth is not None:
            self.config['parameters']['depth'] = depth
        if max_features is not None:
            self.config['parameters']['maxfeat'] = max_features
        self.config['category'] = "classification"
        self.model = model
        self.ml = ML(self.config)

    def train(self, isf_inss, model_file=None, feat_imp_file=None):
        """
        Trains a GBRT classifier and saves the model into a file.

        :param isf_inss: er.ml.ISFInstances
        :param model_file: str, name of file to save the trained model
        :return trained model
        """
        config = self.config
        if model_file is not None:
            config['save_model'] = model_file
        if feat_imp_file is not None:
            config['save_feature_imp'] = feat_imp_file
        self.ml.config = config
        ranker = self.ml.train_model(isf_inss)
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
        kcv = CrossValidation(num_folds, inss, self.train, self.predict)

        # loads/generates folds
        if gen_folds:
            kcv.create_folds(group_by="session")
            if folds_name is not None:
                kcv.save_folds(folds_name)
        else:
            kcv.load_folds(folds_name)
        # Cross validation
        inss = kcv.run()
        inss.__class__ = ISFInstances
        for ins in inss.get_all():
            ins.__class__ = ISFInstance
        return inss

    def predict(self, isf_inss, model=None, threshold=None):
        """
        Predicts labels for the given instances.

        :param isf_inss: erd.ml.ISFInstances
        :param model: trained model (loaded by pickle)
        :return instances with the predicted labels.
        """
        if model is None:  # Done for CV call_back_test method
            model = self.model

        print "Detecting set for ISF instances ..."
        if len(isf_inss.get_all()) == 0:
            return isf_inss
        # adding features
        if len(isf_inss.get_all()[0].features) <= 0:
            self.add_features(isf_inss)
        self.ml.apply_model(isf_inss, model)
        # If LTR is used, we filter entities below the threshold
        # if threshold is not None:
        #     for ins in isf_inss.get_all():
        #         if ins.score >= threshold:
        #             ins.target = "1"
        #         else:
        #             ins.target = "0"
        return isf_inss

    @staticmethod
    def add_features(isf_inss):
        """ generates features of all instances"""
        econfig.FACC_LUCENE.open_reader()
        econfig.FACC_LUCENE.open_searcher()

        print "Extracting features of ISF instances ..."
        i = 0
        for isf_ins in isf_inss.get_all():
            extractor = FeatureExtractor(isf_ins)
            isf_ins.features = extractor.get_features()
            i += 1
            if i % 1000.0 == 0:
                print "Features are generated until instance " + str(i)

        # econfig.FACC_LUCENE.close_reader()

        return isf_inss


class FeatureExtractor(object):
    """
        Extracts features for ISF instances.
        Attribute:
            isf_ins: erd.ml.ISFInstance
    """

    def __init__(self, isf_ins):
        self.isf_ins = isf_ins

    def get_features(self):
        """
        Adds features to the instance.
        Args:
            isf_inss: erd.ml.ISFInstances
        """
        ag = Aggregator(self.isf_ins)
        query_sim_feat = QuerySimFeat(self.isf_ins.q_content)

        en_ids = self.isf_ins.inter_set.keys()
        entities = {}
        for en_id in en_ids:
            entities[en_id] = econfig.ENTITY.lookup_dbpedia_uri(en_id)
        graph_feat = GraphFeat(entities)

        fb_ids = set()
        for en_id in self.isf_ins.inter_set:
            fb_ids.add(self.isf_ins.cer_atts[en_id]['fb_id'])

        features = {}
        # features['num_nodes'] = graph_feat.num_nodes
        # features['num_edges'] = graph_feat.num_edges

        # ------ set-based features ------
        features['common_links'] = graph_feat.common_neighbors()
        features['total_links'] = graph_feat.all_neighbors()
        features['j_kb'] = graph_feat.jc()
        features['j_corpora'] = econfig.FACC_FEAT.jc(fb_ids)
        features['rel_mw'] = econfig.FACC_FEAT.mw_rel(fb_ids)
        features['P'] = econfig.FACC_FEAT.joint_prob(fb_ids)
        features['H'] = econfig.FACC_FEAT.entropy(fb_ids)
        features['completeness'] = graph_feat.completeness()
        features['len_ratio_set'] = self.len_ratio_iset()
        features['set_sim'] = query_sim_feat.query_set_sim(self.isf_ins.inter_set.keys(), {'names': 0.2, 'contents': 0.8})

        # ------ entity-based feature -------
        # num_links
        num_links = [EntityFeat(en_id).links() for en_id in self.isf_ins.inter_set]
        features.update(ag.aggregate(dict(zip(en_ids, num_links)), "links"))
        # commonness
        commonness = [self.isf_ins.cer_atts[en_id]['commonness'] for en_id in en_ids]
        features.update(ag.aggregate(dict(zip(en_ids, commonness)), "commonness"))
        # CER scores
        cer_scores = [self.isf_ins.cer_atts[en_id]['score'] for en_id in en_ids]
        features.update(ag.aggregate(dict(zip(en_ids, cer_scores)), "score"))
        # rank inverse
        iranks = [1.0 / self.isf_ins.cer_atts[en_id]['rank'] for en_id in en_ids]
        features.update(ag.aggregate(dict(zip(en_ids, iranks)), "irank"))
        # MLM-tc
        if "mlm-tc" in self.isf_ins.cer_atts.values()[0]:
            mlm_tc_scores = [self.isf_ins.cer_atts[en_id]['mlm-tc'] for en_id in en_ids]
            features.update(ag.aggregate(dict(zip(en_ids, mlm_tc_scores)), "mlm-tc"))
        # con_sim
        features.update(ag.aggregate(self.context_sim_scores(), "context_sim"))
        return features

    def len_ratio_iset(self):
        """ Calculates: sum(length of all mentions in the set) / query len. """
        iset_men_len = 0
        for _, mention in self.isf_ins.inter_set.iteritems():
            iset_men_len += len(mention.split())
        return float(iset_men_len)/len(self.isf_ins.q_content.split())

    def context_sim_scores(self):
        scores = dict()
        for en_id, mention in self.isf_ins.inter_set.iteritems():
            scores[en_id] = QuerySimFeat(self.isf_ins.q_content).context_sim(en_id, mention)
        return scores

    def mention_sim_scores(self):
        scores = dict()
        for en_id, mention in self.isf_ins.inter_set.iteritems():
            score = QuerySimFeat(mention).nllr_lm_score(en_id)  # lm_score(en_id)
            scores[en_id] = score if score is not None else 0
        return scores

    # def get_connectedness(self, entities):
    #     """average of jc-graph similarity between each two entities in the set."""
    #     if len(entities) < 2:
    #         return {entities.keys()[0]: -1}
    #     conns = {}
    #     en_id_couples = set(combinations(entities.keys(), 2))
    #     for en_id1, en_id2 in en_id_couples:
    #         en_copuple = {en_id1: entities[en_id1], en_id2: entities[en_id2]}
    #         conns[(en_id1, en_id2)] = EntitiesFeat(en_copuple).jc_graph()
    #     return conns

    # def get_cooccurrences(self):
    #     """average of jc-corpus similarity between each two entities in the set."""
    #     fb_ids = set()
    #     for en_id in self.isf_ins.inter_set:
    #         fb_ids.add(self.isf_ins.cer_atts[en_id]['fb_id'])
    #
    #     if len(fb_ids) < 2:
    #         return -1
    #     fb_id_couples = set(combinations(fb_ids, 2))
    #     cooccurrence = 0
    #     for fb_id_couple in fb_id_couples:
    #         cooccurrence += EntitiesFeat.jc_corpus(set(fb_id_couple))
    #     cooccurrence /= len(fb_id_couples)
    #     return cooccurrence


def main(args):
    """
    Required args for training:         -train -t <int> -d <int> -in <train_set_name.json>
    Required args for prediction:       -predict -model <model_file> -in <file.json>
    """
    settings_str = "-t" + str(args.tree)
    if args.depth is not None:
        model_name = "gbrt"
        settings_str += "-d" + str(args.depth)
    elif args.maxfeat is not None:
        model_name = "rf"
        settings_str += "-m" + str(args.maxfeat)

    # ==== Train ====
    if args.train:
        train_inss = ISFInstances.from_json(args.input)
        file_name = args.input[:args.input.rfind(".json")] + settings_str
        set_detector = SetDetect(model_name=model_name, tree=args.tree, depth=args.depth, max_features=args.maxfeat)
        set_detector.train(train_inss, file_name + ".model", feat_imp_file=file_name + "-feat_imp.txt")

    # ==== Cross Validation ====
    elif args.cv:
        in_file_name = args.input[:args.input.rfind(".json")]
        cv_inss = ISFInstances.from_json(args.input)
        set_detector = SetDetect(model_name=model_name, tree=args.tree, depth=args.depth, max_features=args.maxfeat)
        ranked_inss = set_detector.cross_validate(cv_inss, args.folds,
                                                  folds_name=in_file_name + "-" + str(args.folds) + "f-folds.json",
                                                  gen_folds=args.genfolds)
        # If LTR is used, we filter entities below the threshold
        if args.threshold is not None:
            for ins in ranked_inss.get_all():
                if ins.score >= args.threshold:
                    ins.target = "1"
                else:
                    ins.target = "0"
        ranked_inss.to_json(in_file_name + "-" + str(args.folds) + "f" + settings_str + ".json")
        ranked_inss.to_str(in_file_name + "-" + str(args.folds) + "f" + settings_str + ".txt")
        ranked_inss.to_erdeval(in_file_name + "-" + str(args.folds) + "f" + settings_str + ".erdeval")

    # ==== Predict ====
    elif args.predict:
        # loads model
        model = pickle.loads(open(args.model, 'r').read())
        set_detector = SetDetect()

        # Ranks instances
        if args.input is not None:
            inss = ISFInstances.from_json(args.input)
            ranked_inss = set_detector.predict(inss, model, threshold=args.threshold)
            # Writes instances
            settings_str = ""
            isf_params_str = args.model[args.model.rfind("-isf"):]
            if isf_params_str.rfind("-d") != -1:
                settings_str += isf_params_str[isf_params_str.rfind("-t"):isf_params_str.rfind("-d")]
                settings_str += isf_params_str[isf_params_str.rfind("-d"):isf_params_str.rfind(".model")]
            elif isf_params_str.rfind("-m") != -1:
                settings_str += isf_params_str[isf_params_str.rfind("-t"):isf_params_str.rfind("-m")]
                settings_str += isf_params_str[isf_params_str.rfind("-m"):isf_params_str.rfind(".model")]

            file_name = args.input[:args.input.rfind(".json")] + settings_str #+ "-qi"
            ranked_inss.to_json(file_name + ".json")
            # ranked_inss.to_str(file_name + ".txt")
            ranked_inss.to_erdeval(file_name + ".erdeval")
