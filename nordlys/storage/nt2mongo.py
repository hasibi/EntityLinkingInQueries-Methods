"""
Loads NTriples RDF file into MongoDB.

Documents are identified by subject URIs.
Predicate-object values are stored as key-value pairs in a dictionary,
where object can be single-valued (string) or multi-valued (list of strings). 

- Multiple ntriple files can be added to the same collection, where they would 
  be appended to the corresponding document. 
- Empty object values are filtered out, even if they're present in the NTriples
  file (that happens, for example, with DBpedia long abstracts.)

IMPORTANT: 
- It is assumed that all triples with a given subject are grouped 
  together in the .nt file (this holds, e.g., for DBpedia)
- It is also assumed that a given predicate is present only in a single file;
  when that is not the case, the contents in the last processed file will
  overwrite the previously stored values in the given field, corresponding to 
  the predicate. If it can be a problem (e.g., DBpedia uses <rdf:type> for 
  both mapping-based types and YAGO types) then use predicate prefixing!

@author: Krisztian Balog
"""

import sys
import gzip
import logging
from nordlys.storage.mongo import Mongo
from nordlys.parse.uri_prefix import URIPrefix
from rdflib.plugins.parsers.ntriples import NTriplesParser
from rdflib.term import URIRef


class Triple(object):
    """Representation of a Triple to be used by the rdflib NTriplesParser."""

    def __init__(self):
        self.s = None
        self.p = None
        self.o = None

    def triple(self, s, p, o):
        self.s = s
        self.p = p
        self.o = o

    def subject(self):
        return self.s

    def predicate(self):
        return self.p

    def object(self):
        return self.o


class NTriplesToMongoDB(object):
    def __init__(self, host, db, collection):
        self.mongo = Mongo(host, db, collection)
        self.prefix = URIPrefix()
        logging.basicConfig(level="ERROR")  # no warnings from the rdf parser

    def prefix_uri(self, uri):
        """Prefix URI and enclos in between <>."""
        return "<" + self.prefix.get_prefixed(uri) + ">"

    def __next_triple(self, subj, pred, obj):
        """Process a triple.
        - Appends to previous triple if it's the same subject
        - Otherwise inserts last triple and creates a new one"""

        if (self.m_id is not None) and (self.m_id == subj):
            if pred in self.m_contents:
                # if it's not a list (i.e., single value), then make it a list
                if type(self.m_contents[pred]) is not list:
                    self.m_contents[pred] = [self.m_contents[pred]]
                self.m_contents[pred].append(obj)
            else:
                self.m_contents[pred] = obj
        else:
            self.__write_to_mongo()
            self.m_id = subj
            self.m_contents = {}
            self.m_contents[pred] = obj

    def __write_to_mongo(self):
        """Write triple (inserts or appends existing) to MongoDB collection."""
        if self.m_id is not None:
            self.mongo.add(self.m_id, self.m_contents)
            self.m_id = None
            self.m_contents = None

    def get_mongo(self):
        """Returns the MongoDB object."""
        return self.mongo

    def drop(self):
        """Delete the collection."""
        self.mongo.drop()

    def add_file(self, filename, reverse_triple=False, predicate_prefix=None):
        """Add contents from an NTriples file to MongoDB.
        
        Args:
            filename: NTriples file
            reverse_triple: if set True, the subject and object values are swapped
            predicate_prefix: prefix to be added to predicates
        """
        print "Processing " + filename + "..."

        t = Triple()
        p = NTriplesParser(t)
        self.m_id = None  # document id for MongoDB -- subj
        self.m_contents = None  # document contents for MongoDB -- pred, obj
        i = 0

        with self.open_file_by_type(filename) as f:
            for line in f:
                p.parsestring(line)
                if t.subject() is None:  # only if parsed as a triple
                    continue

                # prefixing URIs
                """
                @todo set utf-8 to default in main()
                """
                subj = self.prefix_uri(t.subject().encode("utf-8"))
                pred = self.prefix_uri(t.predicate().encode("utf-8"))

                # predicate prefixing
                if predicate_prefix is not None:
                    pred = predicate_prefix + pred
                if type(t.object()) is URIRef:
                    obj = self.prefix_uri(t.object().encode("utf-8"))
                else:
                    obj = t.object().encode("utf-8")
                    if len(obj) == 0: continue  # skip empty objects

                # write or append
                if reverse_triple:  # reverse subj and obj
                    self.__next_triple(obj, pred, subj)
                else:  # normal mode
                    self.__next_triple(subj, pred, obj)

                i += 1
                if i % 10000 == 0:
                    print str(i / 1000) + "K lines processed"

        # process last triple
        self.__write_to_mongo()

    def open_file_by_type(self, filename):
        """Opens file (gz/text) and returns the handler.

        Args:
            filename: NTriples file
        """
        if (self.file_type(filename) == "gz"):
            return gzip.open(filename, 'r')
        else:
            return open(filename, 'r')

    def file_type(self, filename):
        """Returns type of a file (gz, zip, txt).

        Args:
            filename: NTriples file
        """
        magic_dict = {
            "\x1f\x8b\x08": "gz",
            "\x50\x4b\x03\x04": "zip"
        }

        max_len = max(len(x) for x in magic_dict)

        with open(filename) as f:
            file_start = f.read(max_len)
        for magic, filetype in magic_dict.items():
            if file_start.startswith(magic):
                return filetype
        return "txt"


def main():
    pass


if __name__ == "__main__":
    main()