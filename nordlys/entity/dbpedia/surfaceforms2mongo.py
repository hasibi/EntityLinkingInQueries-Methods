"""
Loads entity surface forms to MongoDB.

This has to be run only once, after DBpedia has been loaded into MongoDB with `dbpedia2mongo.py`.

The following predicates are considered:


@author: "Krisztian Balog"
"""

import argparse
from nordlys.entity.surfaceforms import SurfaceForms
from nordlys.config import MONGO_DB, MONGO_HOST
from nordlys.entity.config import COLLECTION_DBPEDIA
from nordlys.storage.mongo import Mongo
from entity import DBpediaEntity, DBPEDIA_PREDICATE_NAME, DBPEDIA_PREDICATE_REDIRECT


class DBpediaSurfaceForms(SurfaceForms):

    def __init__(self, lowercase=False):
        super(DBpediaSurfaceForms, self).__init__(lowercase)
        self.mongo_dbpedia = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_DBPEDIA)

    def __get_surface_form(self, surface_form):
        """Returns the variant of the surface form that will be stored.
        Currently, this only means lowercaseing (if needed), but additional preprocessing steps may be added here later.
        """
        if self.lowercase:
            return surface_form.lower()
        else:
            return surface_form

    def add_all(self, drop=False):
        """Adds all name variants from DBpedia.
        (It does not delete previously stored variants, but overwrites the fields associated
        with the selected predicates.)

        Args:
            drop: Drop collection before adding content
        """
        if drop:
            self.drop()

        # iterate through all DBpedia entities
        i = 0
        for mdoc in self.mongo_dbpedia.find_all():
            entity = DBpediaEntity(self.mongo.get_doc(mdoc))

            # skip non-entities (disambiguation pages or entities without names)
            if not entity.is_entity():
                continue

            surface_form = self.__get_surface_form(entity.get_name())
            entity_uri = entity.get_uri()

            # titles
            predicate = DBPEDIA_PREDICATE_NAME
            # if redirect, use the uri it redirects to
            if entity.is_redirect():
                entity_uri = entity.get_redirects_to()
                predicate = DBPEDIA_PREDICATE_REDIRECT
            # increase count
            self.inc(surface_form, predicate, entity_uri)

            # <foaf:name> -- only for non-redirects
            if not entity.is_redirect():
                predicate = "<foaf:name>"
                if entity.has_predicate(predicate):
                    # there might be multiple names; therefore, we always treat them as a list
                    surface_forms = entity.get_predicate(predicate)
                    if not isinstance(surface_forms, list):
                        surface_forms = [surface_forms]

                    for sf in surface_forms:
                        surface_form = self.__get_surface_form(sf)
                        self.inc(surface_form, predicate, entity_uri)

            i += 1
            if i % 1000 == 0:
                print str(i / 1000) + "K entities processed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="Command (only add_all is supported ATM)", choices=['add_all'])
    parser.add_argument("-l", "--lowercase", help="Lowercased", action="store_true", dest="lower", default=False)
    parser.add_argument("-d", "--drop", help="Empty collection before adding new content", action="store_true", dest="drop", default=False)
    args = parser.parse_args()

    if args.command == "add_all":
        dbsf = DBpediaSurfaceForms(args.lower)
        dbsf.add_all(args.drop)

if __name__ == '__main__':
    main()