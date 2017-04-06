"""
Entity surface forms stored in MongoDB.

The surface form is used as _id. The associated entities are stored in key-value format, where
- key is a predicate (e.g., <rdfs:label> or <dbo:wikiPageRedirects>)
- value is a dictionary, with URIs and frequecies as keys and values, respectively (e.g., {"<dbpedia:Audi_A4>": 1})

@author: "Krisztian Balog"
"""

from nordlys.config import MONGO_DB, MONGO_HOST
from nordlys.entity.config import COLLECTION_SURFACEFORMS, COLLECTION_SURFACEFORMS_LOWERCASE
from nordlys.storage.mongo import Mongo


class SurfaceForms(object):

    def __init__(self, lowercase=False, collection=None):
        self.lowercase = lowercase
        if collection is not None:
            self.collection = collection
        else:
            if lowercase:
                self.collection = COLLECTION_SURFACEFORMS_LOWERCASE
            else:
                self.collection = COLLECTION_SURFACEFORMS
        self.mongo = Mongo(MONGO_HOST, MONGO_DB, self.collection)

    def drop(self):
        """Drops collection."""
        self.mongo.drop()

    def add(self, surface_form, predicate, value):
        """Replaces the value associated with a given predicate."""
        self.mongo.add(surface_form, predicate, value)

    def inc(self, surface_form, predicate, entity_uri, count=1):
        """Increases the count for the given URI associated with the surface form.
        If the URI is not associated with the surface form yet, it adds it with count."""
        self.mongo.inc_in_dict(surface_form, predicate, entity_uri, count)

    def get(self, surface_form):
        """Returns all information associated with a surface form."""

        # need to unescape the keys in the value part
        mdoc = self.mongo.find_by_id(surface_form)
        if mdoc is None:
            return None
        doc = {}
        for f in mdoc:
            if f != Mongo.ID_FIELD:
                doc[f] = {}
                for key, value in mdoc[f].iteritems():
                    doc[f][Mongo.unescape(key)] = value

        return doc


def main():
    pass

if __name__ == '__main__':
    main()
