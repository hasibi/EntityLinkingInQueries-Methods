"""
Loads Wiki page ids into MongoDB as a separate collection.

This is to be used only once.

@author: Faegheh Hasibi
"""

from nordlys.config import MONGO_DB, MONGO_HOST
from nordlys.entity.config import COLLECTION_PAGE_ID
from nordlys.storage.nt2mongo import NTriplesToMongoDB


class PageId2Mongo(object):

    def __init__(self, filepath):
        self.filepath = filepath

    def build_coll(self):
        """Builds the Wiki page Id to dbpedia uri collection."""
        nt = NTriplesToMongoDB(MONGO_HOST, MONGO_DB, COLLECTION_PAGE_ID)
        nt.drop()

        nt.add_file(self.filepath, reverse_triple=True)


def main():
    path = "home/faeghehh/march-cikm-nordlys-erd/data/erd/page_ids_en.nt"  # @todo: to be moved
    pim = PageId2Mongo(path)
    pim.build_coll()

if __name__ == "__main__":
    main()