"""
DBpedia entity.

@author: "Krisztian Balog"
"""
from nordlys.storage.mongo import Mongo

DBPEDIA_PREDICATE_NAME = "<rdfs:label>"
DBPEDIA_PREDICATE_REDIRECT = "<dbo:wikiPageRedirects>"


class DBpediaEntity(object):
    """Class representing a DBpedia entity."""

    def __init__(self, doc):
        """
        Args:
            doc: document (dict) representing the entity
        """
        self.doc = doc

    def get_uri(self):
        """Returns the (internal, i.e., prefixed) URI of the entity."""
        return self.doc[Mongo.ID_FIELD]

    def get_name(self):
        """Returns the name of a entity (or None)."""
        if DBPEDIA_PREDICATE_NAME in self.doc:
            return self.doc[DBPEDIA_PREDICATE_NAME]
        return None

    def is_entity(self):
        """Checks whether the entity is a real entity.
         It means that it is not a disambiguation page and has name.
         This excludes, e.g., Category and Template pages."""
        return DBPEDIA_PREDICATE_NAME in self.doc and not self.is_disambiguation()

    def is_redirect(self):
        """Checks whether the entity is a redirect."""
        if self.doc is not None:
            # redirect is it has "" predicate
            if DBPEDIA_PREDICATE_REDIRECT in self.doc:
                return True
        return False

    def get_redirects_to(self):
        """Returns the URI the entity redirects to (or None if it's not a redirect)."""
        if DBPEDIA_PREDICATE_REDIRECT in self.doc:
            return self.doc[DBPEDIA_PREDICATE_REDIRECT]
        return None

    def is_disambiguation(self):
        """Checks whether the entity is a disambiguation page.
        It uses the simple heuristic that DBpedia disambiguation pages have _(disambiguation) as suffix to the URL."""
        # note that the _id is in <dbpedia:URI> format
        return self.doc[Mongo.ID_FIELD].endswith("_(disambiguation)>")

    def has_predicate(self, predicate):
        """Checks if the entity has a given predicate."""
        return predicate in self.doc

    def get_predicate(self, predicate):
        """Returns the value of a given predicate."""
        if predicate in self.doc:
            return self.doc[predicate]
        return None


def main():
    pass

if __name__ == "__main__":
    main()
