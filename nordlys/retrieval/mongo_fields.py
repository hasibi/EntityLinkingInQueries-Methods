"""
Tools for Dbpedia fields:
 - Gets the frequency of all fields in Dbpedia collection
 - Get top most frequent fields and store them in mongodb (should be done only once)
 - Retrieves field frequency from Mongo (and other operations...)

@author: Faegheh Hasibi
"""

import json
import sys
from nordlys.retrieval.config import COLLECTION_FIELDS
from nordlys.config import MONGO_HOST, MONGO_DB
from nordlys.storage.mongo import Mongo
from nordlys.entity import config as en_config


class Fields(object):

    def __init__(self, collection_fields=COLLECTION_FIELDS):
        self.mongo = Mongo(MONGO_HOST, MONGO_DB, collection_fields)

    def build(self, doc_collection, n=1000, out_file=None):
        """
        Builds a Mongo collection holding top-n frequent fields.
        Note: This function should be run once, to build the Mongo collection.

        :param n: Number of fields to be considered
        :param out_file: Top fields are written into this file
        """
        self.mongo.drop()

        fields = self.__get_top_fields(doc_collection, n, out_file)
        for field, content in fields.iteritems():
            self.mongo.add(field, content)

    def __get_top_fields(self, doc_collection, n=1000, out_file=None):
        """
        Gets top-n frequent fields from DBpedia
        NOTE: Rank of fields with the same frequency is equal.
              This means that there can more than one field for each rank.

        :param doc_collection:
        :param n: Number of fields to be considered
        :param out_file: Top fields can be saved here
        """
        field_counts = self.__get_field_counts(doc_collection)
        sorted_fields = sorted(field_counts.items(), key=lambda f_c: f_c[1], reverse=True)
        print "Number of total fields:", len(sorted_fields)

        top_fields = dict()
        rank, prev_count, i = 0, 0, 0
        for field, count in sorted_fields:
            # changes the rank if the count number is changed
            i += 1
            if prev_count != count:
                rank = i
            prev_count = count
            if rank > n:
                break
            top_fields[field] = {'count': count, 'rank': rank}
        if out_file is not None:
            json.dump(top_fields, open(out_file, "w"), indent=4)
        return top_fields

    def __get_field_counts(self, doc_collection):
        """
        Reads all documents in the Mongo collection and calculates field frequencies.
            i.e. For DBpedia collection, it returns all entity fields.

        :param doc_collection: The name mongo collection stores all documents/entities.
        :return a dictionary of fields and their frequency
        """
        dbpedia_coll = Mongo(MONGO_HOST, MONGO_DB, doc_collection).find_all()
        i = 0
        field_counts = dict()
        for entity in dbpedia_coll:
            for field in entity:
                if field == Mongo.ID_FIELD:
                    continue
                # fields.append(field)
                if field in field_counts:
                    field_counts[field] += 1
                else:
                    field_counts[field] = 1
            i += 1
            if i % 1000000 == 0:
                print str(i / 1000000) + "M entity is processed!"
        return field_counts

    def get_count(self, field):
        """
        Returns field count in DBpedia collection.

        :param field: Field name
        :return int, number of occurences of field in Mongo docs
        """
        mdoc = self.mongo.find_by_id(field)
        if mdoc is None:
            return None
        return mdoc['count']

    def get_rank(self, field):
        """
        Returns field rank in DBpedia collection, based on frequency.

        :param field: Field name
        :return int, field rank
        """
        mdoc = self.mongo.find_by_id(field)
        if mdoc is None:
            raise Exception("Err: Field \"" + field + "\" not found!")
        return mdoc['rank']

    def get_all(self):
        """Returns all field names."""
        fields = []
        mdocs = self.mongo.find_all()
        for mdoc in mdocs:
            fields.append(mdoc[Mongo.ID_FIELD])
        return fields


def main(args):
    fields = Fields()
    fields.get_count("all")
    # Generate Mongo collection for fields
    if args[0] == "-build":
        fields.build(en_config.COLLECTION_DBPEDIA, out_file="output/top_fields.json")

    # # To test, Prints all fields
    # if args[0] == "-all":
    #     for field in fields.get_all():
    #         print field

if __name__ == "__main__":
    main(sys.argv[1:])