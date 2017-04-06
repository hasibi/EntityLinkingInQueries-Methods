"""
Instance class.

Features:
    - This class supports different features for an instance.
    - The features, together with the id of the instance, will be used in machine learning algorithms.
    - All Features are stored in a dictionary, where keys are feature names (self.features).

Instance properties:
    - Properties are additional side information of an instance (e.g. query_id, entity_id, ...).
    - properties are stored in a dictionary (self.properties).

This is the base instance class.
Specific type of instances can inherit form class and add more properties to the base class.

@author: Faegheh Hasibi
"""

import json


class Instance(object):
    """
    Class attributes:
        ins_id: (string)
        features: a dictionary of feature names and values
        target: (string) target id or class
        properties: a dictionary of property names and values
    """

    def __init__(self, id, features=None, target="0", properties=None):
        self.id = id
        self.target = target
        if features is None:
            self.features = {}
        else:
            self.features = features
        if properties is None:
            self.properties = {}
        else:
            self.properties = properties

    def add_feature(self, feature, value):
        """Adds a new feature to the features.

        :param feature: (string), feature name
        :param value
        """
        self.features[feature] = value

    def get_feature(self, feature):
        """Returns the value of a given feature.

        :param feature
        :return value
        """
        return self.features.get(feature, None)

    def add_property(self, property, value):
        """Adds a new property to the properties.

        :param property: (string), property name
        :param value
        """
        self.properties[property] = value

    # def get_property(self, property):
    #     """Returns the value of a given property.
    #
    #     :param property
    #     :return value
    #     """
    #     return self.properties.get(property, None)

    @classmethod
    def from_json(cls, ins_id, fields):
        """Reads an instance in JSON format and generates Instance.

        :param ins_id: instance id
        :param fields: A dictionary of fields
        :return (ml.Instance)
        """
        instance = cls(ins_id)
        for key, value in fields.iteritems():
            if key == 'target':
                instance.target = value
            elif key == 'properties':
                instance.properties = value
            elif key == 'features':
                for ftr_name, ftr_val in value.iteritems():
                    instance.features[ftr_name] = float(ftr_val)
        return instance

    def to_json(self, file_name=None):
        """Converts instance to the JSON format.

        :param file_name: (string)
        :return JSON dump of the instance.
        """
        json_ins = {self.id: {'target': self.target, 'features': self.features, 'properties': self.properties}}
        if file_name is not None:
            print "writing instance \"" + str(self.id) + "\" to " + file_name + "..."
            out = open(file_name, 'w')
            json.dump(json_ins, out, indent=4)
        return json_ins

    def to_str(self, feature_set=None):
        """ Converts instances to string.

        :param feature_set: features to be included in the output format
        :return (string) tab separated string: ins_id target ftr_1    ftr_2   ...   ftr_n   properties
        """
        if feature_set is None:
            feature_set = sorted(self.features.keys())
        out = str(self.id) + "\t" + str(self.target) + "\t"
        for feature in feature_set:
            out += feature + ":" + str(self.features[feature]) + "\t"
        for field in sorted(self.properties.keys()):
            out += field + ":" + str(self.properties[field]) + "\t"
        return out

    def to_libsvm(self, features, qid_prop=None):
        """
        Converts instance to the Libsvm format.
        - RankLib format:
            <target> qid:<qid> <feature>:<value> ... # <info>
        - Example: 3 qid:1 1:1 2:1 3:0 4:0.2 5:0 # 1A

        NOTE: the property used for qid(qid_prop) should hold integers

        :param features: the list of features that should be in the output
        :param qid_prop: property to be used as qid
        :return str, instance in the rankLib format.
        """
        # Sets qid
        qid = self.id if qid_prop is None else self.get_property(qid_prop)

        out = self.target + " qid:" + str(qid) + " "
        feature_id = 1
        for feature in features:
            out += str(feature_id) + ":" + str(self.features[feature]) + " "
            feature_id += 1
        return out


    # ==================== Parts specific to ERD =========================
    # Score
    @property
    def score(self):
        return self.properties.get('score', None)

    @score.setter
    def score(self, value):
        self.properties['score'] = value

    #Query ID
    @property
    def q_id(self):
        return self.properties.get('q_id', None)

    @q_id.setter
    def q_id(self, value):
        self.properties['q_id'] = value

    #Query Content
    @property
    def q_content(self):
        return self.properties.get('q_content', None)

    @q_content.setter
    def q_content(self, value):
        self.properties['q_content'] = value

    @property
    def session(self):
        # Add  session to its properties
        if ("session" not in self.properties) or (self.properties['session'] is None):
            index = self.q_id.rfind("_")
            if index != -1:
                self.properties['session'] = self.q_id[:index]
            else:
                self.properties['session'] = self.q_id
        return self.properties['session']

    def get_property(self, property):
        """Returns the value of a given property.

        :param property
        :return value
        """
        if property == "session":
            return self.session
        return self.properties.get(property, None)


def main():
    ins = Instance(1, {'f1': "0.5", 'f2': "0.4"}, "rel")
    ins.q_id = "q1"
    ins.q_content = "test query"
    ins_file = "../../src/output/instance.txt"
    print ins.to_json(ins_file)

if __name__ == '__main__':
    main()
