"""
Loads Freebase data into MongoDB.

This is to be used only once.

@author: Jan Rybak
"""

import argparse
from rdflib.plugins.parsers.ntriples import NTriplesParser
from rdflib.term import URIRef

from nordlys.config import MONGO_DB, MONGO_HOST
from nordlys.entity.config import COLLECTION_FREEBASE
from nordlys.storage.mongo import Mongo
from nordlys.storage.nt2mongo import Triple, NTriplesToMongoDB


class FreebaseToMongoDB(object):

    def __init__(self, filepath):
        self.filepath = filepath

    def build_freebase(self):
        """Builds the DBpedia collection."""
        nt = NTriplesToMongoDB(MONGO_HOST, MONGO_DB, COLLECTION_FREEBASE)
        nt.drop()

        nt.add_file(self.filepath)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path",  help="path to Freebase dump (one .gz file)")
    parser.add_argument("command", help="Command", choices=["build_freebase"])
    args = parser.parse_args()

    dbm = FreebaseToMongoDB(args.path)

    if args.command == "build_freebase":
        dbm.build_freebase()

if __name__ == "__main__":
    main()