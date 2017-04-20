"""
Tools for working with MongoDB.

@author: Krisztian Balog
"""

import argparse
import sys
from nordlys.config import MONGO_DB, MONGO_HOST
from pymongo import MongoClient


class Mongo(object):
    """Manages the MongoDB connection and operations."""
    ID_FIELD = "_id"

    def __init__(self, host, db, collection):
        self.client = MongoClient(host)
        self.db = self.client[db]
        self.collection = self.db[collection]
        self.db_name = db
        self.collection_name = collection
        print "Connected to " + self.db_name + "." + self.collection_name

    @staticmethod
    def escape(s):
        """Escapes string (to be used as key or fieldname).
        Replaces . and $ with their unicode eqivalents."""
        return s.replace(".", "\u002e").replace("$", "\u0024")

    @staticmethod
    def unescape(s):
        """Unescapes string."""
        return s.replace("\u002e", ".").replace("\u0024", "$")

    def add(self, doc_id, contents):
        """Adds a document or replaces the contents of an entire document."""
        # escaping keys for content
        c = {}
        for key, value in contents.iteritems():
            c[self.escape(key)] = value

        try:
            self.collection.update({Mongo.ID_FIELD: self.escape(doc_id)},
                               {'$set': c},
                               upsert=True)
        except Exception as e:
            print "\nError (doc_id: " + str(doc_id) + ")\n" + str(e)

    def set(self, doc_id, field, value):
        """Sets the value of a given document field (overwrites previously stored content)."""
        self.collection.update({Mongo.ID_FIELD: self.escape(doc_id)},
                               {'$set': {self.escape(field): value}},
                               upsert=True)

    def append_list(self, doc_id, field, value):
        """Appends the value to a given field that stores a list.
        If the field does not exist yet, it will be created."""
        self.collection.update({Mongo.ID_FIELD: self.escape(doc_id)},
                               {'$push': {self.escape(field)
                                          : {'$each': [value]}}},
                               upsert=True)

    def append_dict(self, doc_id, field, dictkey, value):
        """Appends the value to a given field that stores a dict.
        If the dictkey is already in use, the value stored there will be overwritten.

        Args:
            id: _id
            field: field
            dictkey: key in the dictionary
            value: value to be increased by
        """
        key = self.escape(field) + "." + self.escape(dictkey)
        self.collection.update({Mongo.ID_FIELD: self.escape(doc_id)},
                               {'$set': {key: value}},
                               upsert=True)

    def inc(self, doc_id, field, value):
        """Increments the value of a specified field."""
        self.collection.update({Mongo.ID_FIELD: self.escape(doc_id)},
                               {'$inc': {self.escape(field): value}},
                               upsert=True)

    def inc_in_dict(self, doc_id, field, dictkey, value=1):
        """Increments a value that is inside a dict.

        Args:
            id: _id
            field: field
            dictkey: key in the dictionary
            value: value to be increased by
        """
        key = self.escape(field) + "." + self.escape(dictkey)
        self.collection.update({Mongo.ID_FIELD: self.escape(doc_id)},
                               {'$inc': {key: value}},
                               upsert=True)

    def find_by_id(self, doc_id):
        """Returns all document content for a given document id."""
        return self.get_doc(self.collection.find_one({Mongo.ID_FIELD: self.escape(doc_id)}))

    def find_all(self):
        """Returns a Cursor instance that allows us to iterate over all documents."""
        return self.collection.find()

    def drop(self):
        """Deletes the contents of the given collection (including indices)."""
        self.collection.drop()
        print self.collection_name + " dropped"

    def get_doc(self, mdoc):
        """Returns document contents with with keys and _id field unescaped."""
        if mdoc is None:
            return None

        doc = {}
        for f in mdoc:
            if f == Mongo.ID_FIELD:
                doc[f] = self.unescape(mdoc[f])
            else:
                doc[self.unescape(f)] = mdoc[f]

        return doc

    def get_num_docss(self):
        """ Returns total number of documents in the mongo collection """
        return self.find_all().count()


    @staticmethod
    def print_doc(doc):
        print "_id: " + doc[Mongo.ID_FIELD]
        for key, value in doc.iteritems():
            if key == Mongo.ID_FIELD: continue  # ignore the id key
            if type(value) is list:
                print key + ":"
                for v in value:
                    print "\t" + str(v)
            else:
                print key + ": " + str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("collection", help="name of the collection")
    parser.add_argument("doc_id", help="doc_id to be looked up")
    args = parser.parse_args()

    if args.collection:
        coll = args.collection
    if args.doc_id:
        doc_id = args.doc_id

    mongo = Mongo(MONGO_HOST, MONGO_DB, coll)

    # currently, a single operation (lookup) is supported
    res = mongo.find_by_id(doc_id)
    if res is None:
        print "Document ID " + doc_id + " cannot be found"
    else:
        mongo.print_doc(res)


if __name__ == "__main__":
    main()