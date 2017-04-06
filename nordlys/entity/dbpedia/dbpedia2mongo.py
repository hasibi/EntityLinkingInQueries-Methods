"""
Loads DBpedia data into MongoDB.

This is to be used only once.

@author: Krisztian Balog
"""

import argparse
from rdflib.plugins.parsers.ntriples import NTriplesParser
from rdflib.term import URIRef

from nordlys.config import MONGO_DB, MONGO_HOST
from nordlys.entity.config import COLLECTION_DBPEDIA, COLLECTION_FREEBASE_DBPEDIA
from nordlys.storage.mongo import Mongo
from nordlys.storage.nt2mongo import Triple, NTriplesToMongoDB
from entity import DBpediaEntity, DBPEDIA_PREDICATE_REDIRECT


class DBpediaToMongoDB(object):
    
    def __init__(self, basedir):
        self.basedir = basedir

    def __load_dbpedia_reverse_redirects(self, nt):
        """Adds reverse redirects (all entities redirecting to a given entity)
        to MongoDB. Predicate is prefixed with !
        
        Args:
            nt: NTriplesToMongoDB object
        """
        redirects_file = self.basedir + "redirects_en.nt"
        print "Processing " + redirects_file + "..."
        
        mongo = nt.get_mongo()
        t = Triple()
        p = NTriplesParser(t)    
        i = 0
        
        with open(redirects_file) as f:
            for line in f:                
                p.parsestring(line)
                if t.subject() is None: # only if parsed as a triple
                    continue
                
                # prefixing URIs
                """ 
                @todo set utf-8 to default in main()
                """ 
                subj = nt.prefix_uri(t.subject().encode("utf-8"))
                # predicate is prefixed with !
                pred = "!" + nt.prefix_uri(t.predicate().encode("utf-8"))
                if type(t.object()) is URIRef:
                    obj = nt.prefix_uri(t.object().encode("utf-8"))
                else:
                    continue

                # <Subj redirects to Obj> is stored by appending
                # Subj to the !redirects field of Obj
                mongo.append_list(obj, pred, subj)
                                
                i += 1
                if i % 10000 == 0: 
                    print str(i / 1000) + "K lines processed"
                
    def build_dbpedia_39(self):
        """Builds the DBpedia collection."""
        nt = NTriplesToMongoDB(MONGO_HOST, MONGO_DB, COLLECTION_DBPEDIA)
        nt.drop()
        
        for filename in ["labels_en.nt",
                         "instance_types_en.nt",
                         "instance_types_heuristic_en.nt",
                         "mappingbased_properties_cleaned_en.nt",
                         "short_abstracts_en.nt",
                         "long_abstracts_en.nt",
                         "article_categories_en.nt",
                         "wikipedia_links_en.nt",
                         "page_links_en.nt",
                         "redirects_en.nt",
                         "freebase_links.nt"]:
            nt.add_file(self.basedir + filename)

        # YAGO types prefixed with yago:
        nt.add_file(self.basedir + "yago_types.nt", False, "yago:")
        # reverse redirects
        self.__load_dbpedia_reverse_redirects(nt)

    def build_freebase_dbpedia(self):
        """Builds the Freebase to DBpedia collection."""
        nt = NTriplesToMongoDB(MONGO_HOST, MONGO_DB, COLLECTION_FREEBASE_DBPEDIA)
        nt.drop()
        # subject and object need to be reversed
        nt.add_file(self.basedir + "freebase_links.nt", True)

    def check_errors(self, fix_errors=False):
        """Check the stored DBpedia collection for errors.
        Currently the only known issue dealt with here is duplicate redirect values.

        Args:
            fix_errors: Fixes errors as well
        """
        mongo = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_DBPEDIA)
        if fix_errors:
            print "Fixing errors"
        else:
            print "Only listing errors"

        # iterate through MongoDB contents
        i = 0
        for mdoc in mongo.find_all():
            entity = DBpediaEntity(mongo.get_doc(mdoc))
            if not entity.is_entity():
                continue
            if entity.is_redirect():
                redirects = entity.get_redirects_to()
                # redirect value is a list, not a single URI
                if isinstance(redirects, list):
                    print entity.get_uri()
                    print redirects
                    print ""
                    if fix_errors:
                        # replace value with the first element of the list
                        # (all elements of the list are the same)
                        mongo.set(entity.get_uri(), DBPEDIA_PREDICATE_REDIRECT, redirects[0])
                        """
                        @todo
                        the reverse redirects field (of redirects[0]) also contains duplicates
                        in this case -- that should be fixed too
                        """
            i += 1
            if i % 1000 == 0:
                print str(i / 1000) + "K entities checked"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="path to DBpedia dump (.nt files)")
    parser.add_argument("command", help="Command", choices=["build_dbpedia", "build_freebase_dbpedia", "check_errors"])
    parser.add_argument("--fix-errors", help="Errors are not just listed but also fixed", action="store_true",
                        dest="fix", default=False)
    args = parser.parse_args()

    dbm = DBpediaToMongoDB(args.path)

    if args.command == "build_dbpedia":
        dbm.build_dbpedia_39()
    elif args.command == "build_freebase_dbpedia":
        dbm.build_freebase_dbpedia()
    elif args.command == "check_errors":
        dbm.check_errors(args.fix)

if __name__ == "__main__":
    main()