"""
Classes for CER instances.
"CERIns" and "CERInss" class inherit from Instance and Instances class.

Additional properties:
    - Entity ID (dbpedia ID)
    - Freebase ID
    - Mention
    - Interpretation set ID
    - Commonness
    - matches
    - Rank

Additional functions:
    - convert to treceval format
    - sort instances of each query based on score

@author: Faegheh Hasibi
"""
import argparse
import json
import sys
from nordlys.ml.instance import Instance
from nordlys.ml.instances import Instances
from nordlys.erd import econfig


class CERInstance(Instance):
    """
    Instance class for Candidate Entity Ranking (CER).
    The attributes are the same as Instance, only extra properties are added.

    Attributes:
        Similar to class Instance
    """

    def __init__(self, ins_id, features=None, label="0", properties=None):
        Instance.__init__(self, ins_id, features, label, properties)

    @classmethod
    def from_json(cls, ins_id, fields):
        """ Reads an instance in JSON format and generates Instance. """
        ins = Instance.from_json(ins_id, fields)
        ins.__class__ = cls
        return ins

    # Entity ID
    @property
    def en_id(self):
        return self.properties.get('en_id', None)

    @en_id.setter
    def en_id(self, value):
        self.properties['en_id'] = value

    # Freebase ID
    @staticmethod
    def gen_freebase_id(en_id):
        """ Converts wiki id of entity to freebase id. """
        return econfig.ENTITY.dbp_uri_to_fb_id(en_id)

    @property
    def freebase_id(self):
        if not 'fb_id' in self.properties:
            raise Exception("No freebase id is set for the entity " + self.en_id)
        fb_id = self.properties['fb_id']
        return fb_id

    @freebase_id.setter
    def freebase_id(self, value):
        self.properties['fb_id'] = value

    # Mention
    @property
    def mention(self):
        return self.properties.get('mention', None)

    @mention.setter
    def mention(self, value):
        self.properties['mention'] = value

    # Interpretation set ID
    @property
    def set_id(self):
        return self.properties.get('set_id', None)

    @set_id.setter
    def set_id(self, value):
        self.properties['set_id'] = value

    # commonness
    @property
    def commonness(self):
        return self.properties.get('commonness', None)

    @commonness.setter
    def commonness(self, value):
        self.properties['commonness'] = value

    # matches
    @property
    def matches(self):
        return self.properties.get('matches', None)

    @matches.setter
    def matches(self, value):
        self.properties['matches'] = value

    #Rank
    @property
    def rank(self):
        return self.properties.get('rank', None)

    @rank.setter
    def rank(self, value):
        self.properties['rank'] = value

    def to_treceval(self, run_id, use_dbp=False):
        """
        Generates trec-eval output: query_id, iter, docno, rank, sim, run_id
        Args:
            run_id: name of run

        Returns:
            string of trec-eval content
        """

        entity_id = self.en_id if use_dbp else self.freebase_id
        # print self.q_id , entity_id ,  str(self.rank), str(self.score) , "*****"
        out = self.q_id + "\t" + "Q0" + "\t" + entity_id + "\t" + str(self.rank) + "\t" + str(self.score) + "\t" + run_id
        return out


class CERInstances(Instances):
    """ Instances for Candidate Entity Ranking(CER). """

    def __init__(self, instance_list=None):
        Instances.__init__(self, instance_list)

    @classmethod
    def from_json(cls, json_file):
        """ Overriding method of Instances class """
        print "-Input file:\t" + json_file + "\n"
        json_data = open(json_file)
        data = json.load(json_data)
        instance_list = {}
        # read instances
        for ins_id, fields in data.iteritems():

            instance = CERInstance.from_json(ins_id, fields)
            instance_list[instance.id] = instance
        return cls(instance_list)

    @classmethod
    def concatenate_inss(cls, inss_list):
        """ Overriding method of Instances class """
        inss = Instances.concatenate_inss(inss_list)
        inss.__class__ = cls
        return inss

    @staticmethod
    def gen_instances(query, commonness_th, candidate_entities=None, ftr_func=None, sf_source=None, filter=True):
        """
        Generates instances from the candidate entities of the query.
        - Instance id is an integer
        - Instances that are not in Freebase, will be excluded.

        Args:
            query: query.Query
            ftr_func: a function in form of
                ftr_func(entity_id, query, surface) that generates features

        Returns:
            ins.Instances
        """
        print "Generating instances for query " + query.id
        if candidate_entities is None:
            candidate_entities = query.get_candidate_entities(commonness_th, filter=filter)

        instances = CERInstances(None)
        ins_id = 0
        # num_all_matches: number of entities above cmn-threshold, but not filtered by KB snapshot
        for mention, (filtered_matches, num_unfiltered_matches) in candidate_entities.iteritems():
            for (dbp_uri, fb_id), commonness in filtered_matches.iteritems():
                # Generate CERInstance object
                ins = CERInstance(ins_id)
                ins.en_id = dbp_uri
                ins.freebase_id = fb_id
                if ftr_func is not None:
                    features = ftr_func(dbp_uri, query, mention)
                    ins.features = features
                ins.q_id = query.id
                ins.q_content = query.content
                ins.mention = mention
                ins.commonness = commonness
                ins.matches = num_unfiltered_matches
                instances.add_instance(ins)
                ins_id += 1
        return instances

    def sort(self):
        """ Sorts instances according to the scores and assign them rank number. """

        inss_by_query = self.group_by_query()
        for inss_list in inss_by_query.values():
            ins_score = []
            for ins in inss_list:
                # if ins.score is not None:
                ins_score.append((ins.id, ins.score))
            if len(ins_score) == 0:
                continue
            # sort
            sorted_inss = sorted(ins_score, key=lambda item: item[1], reverse=True)
            rank = 0
            uniq_ens = set()
            for (ins_id, score) in sorted_inss:
                ins = self.get_instance(ins_id)
                if ins.freebase_id not in uniq_ens:
                    uniq_ens.add(ins.freebase_id)
                    rank += 1
                ins.rank = rank

    def to_treceval(self, run_id, file_name, use_dbp=False):
        """
        Generates the DocRank format for TREC eval
        NOTE: If there is an entity ranked more than one for the same query,
            the one with higher score is kept.
        """
        unique_entries = dict()  # to keep unique entries of (query_id, entity_id)
        # sort and rank entities
        self.sort()
        for ins in self.get_all():
            if ins.score is not None:
                entry = (ins.q_id, ins.freebase_id)
                if (entry not in unique_entries) or (unique_entries[entry][1] < ins.score):
                    unique_entries[entry] = (ins.id, ins.score)


        open(file_name, 'w').close()
        out_file = open(file_name, 'a')
        out = ""
        counter = 0
        sorted_entries = sorted(unique_entries.keys(), key=lambda item:item[0])
        for entry in sorted_entries:
            ins_id = unique_entries[entry][0]
            out += self.get_instance(ins_id).to_treceval(run_id, use_dbp) + "\n"
            counter += 1
            if (counter % 1000) == 0:
                out_file.write(out)
                out = ""

        out_file.write(out)
        print "Trec-eval output:\t" + file_name

    def to_tsv(self, file_name):

        inss_by_qid = self.group_by_query()

        open(file_name, "w").close()
        out_file = open(file_name, 'a')
        out_str = "qid\tmention\tdbpedia_uri\tfreebase_id\tscore\tcommonness\n"
        counter = 0
        for _, ins_list in sorted(inss_by_qid.items(), key=lambda item:item[0]):
            for ins in ins_list:
                out_str += ins.q_id + "\t" + ins.mention + "\t" + ins.en_id + "\t" + ins.freebase_id + "\t" + \
                           str(ins.score) + "\t" + str(ins.commonness) + "\n"
            counter += 1
        if (counter % 10000) == 0:
            out_file.write(out_str)
            out_str = ""
            print counter, "-th instance is processed!"
        out_file.write(out_str)
        print ".tsv output:" + file_name


def main(args):
    input = args[0]
    # parser = argparse.ArgumentParser()
    # parser.add_argument("-in", "--input", help="Input file from previous step", type=str)
    # args = parser.parse_args()

    # converts json file to treceval
    print input, "*********************"
    input_inss = CERInstances.from_json(input)
    input_inss.to_tsv(input[:input.rfind(".")] + ".tsv")
    # run_id = input[:input.rfind(".")]
    # input_inss.to_treceval(run_id, run_id + ".treceval", use_dbp=False)


if __name__ == "__main__":
    main(sys.argv[1:])