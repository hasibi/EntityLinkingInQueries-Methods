"""
Instance and Instances class for CER instances.
Additional properties:
    - interpretation set
    - set of entity scores (from CER phase)

Additional functions:
    - Convert instances to erd-evaluation format

@author: Faegheh Hasibi
"""
import json
import sys
from nordlys.erd.ml.cer_instances import CERInstance

from nordlys.ml.instance import Instance
from nordlys.ml.instances import Instances


class ISFInstance(Instance):
    """
    Instance class for Interpretation Set Finding (ISF).
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

    @classmethod
    def cer_to_isf(cls, cer_inss, score, isf_ins_id=0):
        """
        Creates an ISF instance from the given CER instances of an interpretation set.

        :param cer_inss: erd.ml.CERInstances, cer instances for an interpretation ser
        :param isf_ins_id: int, id of new instance
        :param score: float, score of the instance
        """

        if len(cer_inss.get_all()) == 0:
            return None

        iset = {}
        first_ins = cer_inss.get_all()[0]
        q_id, q_content = first_ins.q_id, first_ins.q_content
        for ins in cer_inss.get_all():
            iset[ins.en_id] = ins.mention
        isf_ins = ISFInstance(isf_ins_id)
        isf_ins.inter_set = iset
        isf_ins.q_id = q_id
        isf_ins.q_content = q_content
        isf_ins.score = score
        return isf_ins

    #inter_set: A dictionary in the form of {dbpedia_uri: mention, ...}
    @property
    def inter_set(self):
        return self.properties.get('inter_set', None)

    @inter_set.setter
    def inter_set(self, value):
        self.properties['inter_set'] = value

    #cer_atts: A dictionary in the form of {en_id: {score: xxx, rank: xxx, commonness:xxx}, ...}
    @property
    def cer_atts(self):
        return self.properties.get('cer_atts', None)

    @cer_atts.setter
    def cer_atts(self, value):
        self.properties['cer_atts'] = value

    #ranks: A dictionary in the form of {dbpedia_uri: rank, ...}
    @property
    def ranks(self):
        return self.properties.get('ranks', None)

    @ranks.setter
    def ranks(self, value):
        self.properties['ranks'] = value

    #commonness: A dictionary in the form of {dbpedia_uri: commonness, ...}
    @property
    def commonness(self):
        return self.properties.get('commonness', None)

    @commonness.setter
    def commonness(self, value):
        self.properties['commonness'] = value

    def to_erdeval(self):
        """
         Converts instance to the format for erd evaluation:
            -Tab separated string:  query_id    score   en1 en2 ...
        """
        out = ""
        if (self.inter_set is not None) and (self.target is not None):
            out += self.q_id + "\t" + str(self.score)
            for en_id in set(self.inter_set.keys()):
                fb_id = CERInstance.gen_freebase_id(en_id)
                out += "\t" + fb_id
        return out


class ISFInstances(Instances):
    """ Instances for Interpretation Set Finding (ISF). """

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
            instance = ISFInstance.from_json(ins_id, fields)
            instance_list[instance.id] = instance
        return cls(instance_list)

    @classmethod
    def concatenate_inss(cls, inss_list):
        """ Overriding method of Instances class """
        inss = Instances.concatenate_inss(inss_list)
        inss.__class__ = cls
        return inss

    def to_erdeval(self, file_name=None):
        """
        Converts instances to the format for erd evaluation:
            -Tab separated file:  query_id    score   en1 en2 ...
        """
        out = ""
        inss_by_query = self.group_by_query()
        for qid in sorted(inss_by_query.keys()):
            inss_list = inss_by_query[qid]
            unique_entries = set()
            ins_score = [(ins.id, ins.score) for ins in inss_list]
            for ins_id, _ in sorted(ins_score, key=lambda item: item[1], reverse=True):  #inss_list:
                ins = self.get_instance(ins_id)
                if str(ins.target) == "1":
                    entry = tuple(sorted(ins.inter_set.keys()))
                    if entry not in unique_entries:
                        out += ins.to_erdeval() + "\n"
                        unique_entries.add(entry)
        if file_name is not None:
            open(file_name, "w").write(out)
            print "Erd-eval:\t" + file_name
        return out

if __name__ == "__main__":
    test_inss = ISFInstances.from_json(sys.argv[1])
    test_inss.to_erdeval(sys.argv[1][:sys.argv[1].rfind(".")] + ".erdeval")
