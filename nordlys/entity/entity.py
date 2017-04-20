"""
Tools for working with DBpedia and Freebase entities.
This is the main entry point for command line usage.

Current functionality:
- mention-based lookup in DBpedia and Freebase
- URI-based DBpedia lookup
- sameAs lookup DBpedia<->Freebase (i.e., DBpedia URI given a Freebase ID)

See the [wiki](https://bitbucket.org/kbalog/nordlys/wiki/Entity) for further details.

It requires the following MongoDB collections:
- DBpedia collection (COLLECTION_DBPEDIA defined in dbpedia/config.py)
- DBpedia name variants (COLLECTION_DBPEDIA_NV defined in dbpedia/config.py)
- Freebase name variants (COLLECTION_FREEBASE_NV defined in freebase/config.py)
- Freebase to DBpedia (COLLECTION_FREEBASE_DBPEDIA defined in freebase/config.py)

@author: Krisztian Balog
@author: Faegheh Hasibi
"""

import argparse
import pprint

from nordlys.config import MONGO_DB, MONGO_HOST
from nordlys.entity.freebase.utils import FreebaseUtils
from nordlys.storage.mongo import Mongo
from surfaceforms import SurfaceForms
from dbpedia.entity import DBpediaEntity
from config import COLLECTION_DBPEDIA, COLLECTION_FREEBASE, COLLECTION_FREEBASE_DBPEDIA

class Entity(object):
    
    def __init__(self):
        self.mongo_dbpedia = None
        self.mongo_freebase = None
        self.mongo_freebase_dbpedia = None

    def __init_dbpedia(self):
        if self.mongo_dbpedia is None:
            self.mongo_dbpedia = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_DBPEDIA)

    def __init_freebase(self):
        if self.mongo_freebase is None:
            self.mongo_freebase = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_FREEBASE)

    def __init_freebase_dbpedia(self):
        if self.mongo_freebase_dbpedia is None:
            self.mongo_freebase_dbpedia = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_FREEBASE_DBPEDIA)
    
    def lookup_dbpedia_uri(self, uri):
        """Looks up a DBpedia entity by URI.
        
        :param uri: in prefixed format, e.g., "<dbpedia:Audi_A4>"
        :return A dictionary with the entity document or None.
        """
        self.__init_dbpedia()
        return self.mongo_dbpedia.find_by_id(uri)

    def lookup_freebase_uri(self, uri):
        """Looks up a Freebase entity by URI.

        :param uri: in prefixed format, e.g., "<dbpedia:Audi_A4>"
        :return A dictionary with the entity document or None.
        """
        self.__init_freebase()
        return self.mongo_freebase.find_by_id(uri)

    def is_dbpedia_redirect(self, uri):
        """Checks whether the DBpedia URI is a redirect.

        :param uri: in prefixed format, e.g., "<dbpedia:Audi_A4>"
        :return True (if redirect) otherwise False
        """
        self.__init_dbpedia()
        entity = DBpediaEntity(self.mongo_dbpedia.find_by_id(uri))
        return entity.is_redirect()

    def dbp_uri_to_fb_uri(self, dbpedia_uri):
        """Looks up the sameAs Freebase URI for a DBpedia URI.

        :param dbpedia_uri: DBpedia URI
        :return: Freebase URI or None
        """
        self.__init_dbpedia()
        res = self.mongo_dbpedia.find_by_id(dbpedia_uri)
        if res is not None:
            if "<owl:sameAs>" in res:
                uris = res['<owl:sameAs>']
                # make sure we have a list, even if it has a single element
                if not isinstance(uris, list):
                    uris = [res['<owl:sameAs>']]
                # there might be sameAs links for multiple collections,
                # not just Freebase; we need to iterate through them
                for uri in uris:
                    if uri.startswith("<fb:"):
                        return uri
        return None

    def fb_uri_to_dbp_uri(self, freebase_uri):
        """Looks up the sameAs DBpedia URI for a Freebase URI.
        
        :param freebase_uri: Freebase URI
        :return: DBpedia URI or None
        """        
        self.__init_freebase_dbpedia()        
        res = self.mongo_freebase_dbpedia.find_by_id(freebase_uri)
        if res is not None:
            same_as = res['<owl:sameAs>']
            # list -- check URIs for redirects
            if isinstance(same_as, list):
                # return the first one that is not a redirect
                for dbpedia_uri in same_as:
                    if not self.is_dbpedia_redirect(dbpedia_uri):
                        return dbpedia_uri
            # single value -- return
            else:
                return same_as 
        return None

    def dbp_uri_to_fb_id(self, dbpedia_uri):
        """
        Converts DBpedia URI to Freebase Id.

        :param dbpedia_uri: in prefixed format, e.g., "<dbpedia:Audi_A4>"
        :return Freebase Id or None
        """
        fb_uri = self.dbp_uri_to_fb_uri(dbpedia_uri)
        if fb_uri is None:
            return None
        else:
            return FreebaseUtils.freebase_uri_to_id(fb_uri)

    def fb_id_to_dbp_uri(self, freebase_id):
        """
        Converts Freebase Id to DBpedia URI.

        :param uri: Freebase Id
        :return DBpedia URI
        """
        fb_uri = FreebaseUtils.freebase_id_to_uri(freebase_id)
        return self.fb_uri_to_dbp_uri(fb_uri)

    def wiki_uri_to_dbp_uri(self, wiki_uri):
        """Converts Wikipedia uri to DBpedia URI."""
        return wiki_uri.replace("<wikipedia:", "<dbpedia:")

    def dbp_uri_to_wiki_uri(self, dbp_uri):
        """Converts DBpedia uri to Wikipedia URI."""
        return dbp_uri.replace("<dbpedia:", "<wikipedia:")


    @staticmethod
    def is_dbpedia_uri(value):
        """ Returns true if the value is a DBpedia URI. """
        if value.startswith("<dbpedia:") and value.endswith(">"):
            return True
        return False

    @staticmethod
    def is_uri(value):
        """ Returns true if the value is a URI. """
        if value.startswith("<") and value.endswith(">"):
            return True
        return False


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="Command", choices=['lookup_name', 'lookup_dbpedia', 'is_dbpedia_redirect',
                                                            'dbpedia_to_freebase', 'freebase_to_dbpedia',
                                                            'lookup_freebase'])
    parser.add_argument("uri_or_name", help="entity URI or name")
    parser.add_argument("-l", "--lowercase", help="Lowercase, only for name-based lookup", action="store_true",
                        dest="lower", default=False)
    parser.add_argument("-wiki", help="Use Wikipedia name variants", action="store_true", default=False)
    args = parser.parse_args()

    if args.command == "lookup_name":
        sf = SurfaceForms(lowercase=args.lower)
        pprint.pprint(sf.get(args.uri_or_name.lower()))
    else:
        entity = Entity()
        if args.command == "lookup_dbpedia":
            pprint.pprint(entity.lookup_dbpedia_uri(args.uri_or_name))
        if args.command == "lookup_freebase":
            pprint.pprint(entity.lookup_freebase_uri(args.uri_or_name))
        elif args.command == "dbpedia_to_freebase":
            pprint.pprint(entity.dbp_uri_to_fb_uri(args.uri_or_name))
        elif args.command == "is_dbpedia_redirect":
            print "Is " + args.uri_or_name + " a redirect? " + str(entity.is_dbpedia_redirect(args.uri_or_name))
        elif args.command == "freebase_to_dbpedia":
            pprint.pprint(entity.fb_uri_to_dbp_uri(args.uri_or_name))

if __name__ == "__main__":
    main()