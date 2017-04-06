"""
Methods for entity-mention features.

NOTE: This class does not perform any pre-processing on the mention.
Removal of special characters and encodings should be performed before.

@author: Faegheh Hasibi
"""
from nordlys.erd import econfig
from nordlys.erd.query.query import Mention, Query


class EntityMentionFeat(object):
    """
    Attributes:
        entity_id: DBpedia uri of entity (string)
        Mention: string
        entity: All predicates of entity
    """

    def __init__(self, entity_id, mention):
        self.entity_id = entity_id
        self.mention = mention.lower()  # Mention(mention)
        self.entity = {}
        self.entity = econfig.ENTITY.lookup_dbpedia_uri(entity_id)

    def mct(self):
        """ True if mention contains the title of entity """
        mct = 0
        if econfig.TITLE in self.entity:
            en_title = Query.preprocess(self.entity[econfig.TITLE]).lower()
            if en_title in self.mention:
                mct = 1
        return mct

    def tcm(self):
        """ True if title of entity contains mention """
        tcm = 0
        if econfig.TITLE in self.entity:
            en_title = Query.preprocess(self.entity[econfig.TITLE]).lower()
            if self.mention in en_title:
                tcm = 1
        return tcm

    def tem(self):
        """ True if title of entity equals mention """
        tem = 0
        if econfig.TITLE in self.entity:
            en_title = Query.preprocess(self.entity[econfig.TITLE]).lower()
            # if self.entity_id == "<dbpedia:Cass_County,_Missouri>":
            #     print "MENTION:", self.mention, "TITLE:", en_title, "RES:", self.mention == en_title
            if self.mention == en_title:
                tem = 1
        return tem

    def pos1(self):
        """ Position of the occurrence of mention in the short abstract """
        pos1 = 1000
        if econfig.SHORT_ABS in self.entity:
            s_abs = self.entity[econfig.SHORT_ABS].lower()
            if self.mention in s_abs:
                pos1 = s_abs.find(self.mention)
        return pos1

    def commonness(self, sf_source):
        """
        Calculates commonness: (times mention is linked) / (times mention linked to entity)
            - Returns zero if the entity is not linked by the mention.
        """
        mention_obj = Mention(self.mention, sf_source)
        return mention_obj.calc_commonness(self.entity_id)


def main():
    # m1 = "the music man"
    # m2 = "uss yorktown charleston sc"
    # m3 = "the Beatles Rock Band"
    # m3 = "hawaii real estate family resale OR foreclosure"
    # m5 = "yahoo! travel"

    # en = "<dbpedia:New_York>"
    # en1 = "<dbpedia:The_Beatles:_Rock_Band>"
    # en2 = "<dbpedia:Charleston,_South_Carolina>"
    # en3 = "<dbpedia:The_Music_Man_(film)>"
    # en4 = "<dbpedia:Bishopric_of_Utrecht>"
    # en5 = "<dbpedia:University_of_Dayton>"
    # en4 = "<dbpedia:Yahoo!>"
    en3 = "<dbpedia:Kris_Jenner>"
    extractor = EntityMentionFeat(en3, "jenner")
    print extractor.commonness()
   # print extractor.mct()
   # print extractor.tcm()
   # print extractor.tem()
   # print extractor.pos1()


if __name__ == '__main__':
    main()
