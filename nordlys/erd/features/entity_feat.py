"""
Methods for entity features.

@author: Faegheh Hasibi
"""

import sys

from nordlys.erd import econfig


class EntityFeat(object):
    """
    Attributes:
        entity_id: DBpedia uri of entity (string)
    """

    def __init__(self, entity_id):
        self.entity_id = entity_id
        self.entity = {}
        self.entity = econfig.ENTITY.lookup_dbpedia_uri(entity_id)

    def redirects(self):
        """ Number of redirect pages linking to the entity"""
        if econfig.IREDIRECT in self.entity:
            reds = self.entity[econfig.IREDIRECT]
            if type(reds) != list:
                reds = [reds]
            return len(set(reds))
        else:
            return 0

    def links(self):
        """ Number of Wikipedia pages linking to the entity"""
        links = self.entity.get(econfig.WIKILINKS, [])
        if type(links) != list:
            links = [links]
        return len(set(links))


def main(argv):
    # en = "<dbpedia:New_York>"
    # en1 = "<dbpedia:The_Beatles:_Rock_Band>"
    # en2 = "<dbpedia:Charleston,_South_Carolina>"
    # en3 = "<dbpedia:The_Music_Man_(film)>"
    # en4 = "<dbpedia:Bishopric_of_Utrecht>"
    # en5 = "<dbpedia:Yahoo!>"
    extractor = EntityFeat(argv[0])

    print extractor.redirects()
#    print extractor.links()

if __name__ == '__main__':
    main(sys.argv[1:])
