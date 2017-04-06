"""
Tools for Lucene.
All Lucene features should be accessed in nordlys through this class. 

- Lucene class for ensuring that the same version, analyzer, etc. 
  are used across nordlys modules. Handles IndexReader, IndexWriter, etc.  
- Command line tools for checking indexed document content

@author: Krisztian Balog
@author: Faegheh Hasibi
"""
import argparse

import sys
import lucene
from nordlys.storage.mongo import Mongo
from nordlys.retrieval.results import RetrievalResults
from java.io import File
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.document import Document
from org.apache.lucene.document import Field
from org.apache.lucene.document import FieldType
from org.apache.lucene.index import FieldInfo
from org.apache.lucene.index import MultiFields
from org.apache.lucene.index import IndexWriter
from org.apache.lucene.index import IndexWriterConfig
from org.apache.lucene.index import DirectoryReader 
from org.apache.lucene.index import Term
from org.apache.lucene.queryparser.classic import QueryParser
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.search import BooleanClause
from org.apache.lucene.search import TermQuery
from org.apache.lucene.search import BooleanQuery
from org.apache.lucene.search import PhraseQuery
from org.apache.lucene.search import FieldValueFilter
from org.apache.lucene.search.similarities import LMJelinekMercerSimilarity
from org.apache.lucene.search.similarities import LMDirichletSimilarity
from org.apache.lucene.search.similarities import Similarity
from org.apache.lucene.store import SimpleFSDirectory
from org.apache.lucene.store import RAMDirectory
from org.apache.lucene.util import BytesRefIterator
from org.apache.lucene.util import Version
from org.apache.lucene.search import DocIdSetIterator
from org.apache.lucene.analysis.tokenattributes import CharTermAttribute
from org.apache.lucene.index import AtomicReader
from org.apache.lucene.store import IOContext

# has java VM for Lucene been initialized
lucene_vm_init = False


class Lucene(object):

    # default fieldnames for id and contents
    FIELDNAME_ID = "id"
    FIELDNAME_CONTENTS = "contents"

    # internal fieldtypes
    # used as Enum, the actual values don't matter
    FIELDTYPE_ID = "id"
    FIELDTYPE_ID_TV = "id_tv"
    FIELDTYPE_TEXT = "text"
    FIELDTYPE_TEXT_TV = "text_tv"
    FIELDTYPE_TEXT_TVP = "text_tvp"

    def __init__(self, index_dir, use_ram=False, jvm_ram=None):
        global lucene_vm_init
        if not lucene_vm_init:
            if jvm_ram:
                # e.g. jvm_ram = "8g"
                print "Increased JVM ram"
                lucene.initVM(vmargs=['-Djava.awt.headless=true'], maxheap=jvm_ram)
            else:
                lucene.initVM(vmargs=['-Djava.awt.headless=true'])
            lucene_vm_init = True
        self.dir = SimpleFSDirectory(File(index_dir))

        self.use_ram = use_ram
        if use_ram:
            print "Using ram directory..."
            self.ram_dir = RAMDirectory(self.dir, IOContext.DEFAULT)
        self.analyzer = None
        self.reader = None
        self.searcher = None
        self.writer = None
        self.ldf = None
        print "Connected to index " + index_dir

    def get_version(self):
        """Get Lucene version."""
        return Version.LUCENE_48

    def get_analyzer(self):
        """Get analyzer."""
        if self.analyzer is None:
            self.analyzer = StandardAnalyzer(self.get_version())
        return self.analyzer

    def open_reader(self):
        """Open IndexReader."""
        if self.use_ram:
            print "reading from ram directory ..."
            self.reader = DirectoryReader.open(self.ram_dir)
        if self.reader is None:
            self.reader = DirectoryReader.open(self.dir)

    def get_reader(self):
        return self.reader

    def close_reader(self):
        """Close IndexReader."""
        if self.reader is not None:
            self.reader.close()
            self.reader = None
        else:
            raise Exception("There is no open IndexReader to close")

    def open_searcher(self):
        """
        Open IndexSearcher. Automatically opens an IndexReader too,
        if it is not already open. There is no close method for the
        searcher.
        """
        if self.searcher is None:
            self.open_reader()
            self.searcher = IndexSearcher(self.reader)

    def get_searcher(self):
        """Returns index searcher (opens it if needed)."""
        self.open_searcher()
        return self.searcher

    def set_lm_similarity_jm(self, method="jm", smoothing_param=0.1):
        """
        Set searcher to use LM similarity.

        :param method: LM similarity ("jm" or "dirichlet")
        :param smoothing_param: smoothing parameter (lambda or mu)
        """
        if method == "jm":
            similarity = LMJelinekMercerSimilarity(smoothing_param)
        elif method == "dirichlet":
            similarity = LMDirichletSimilarity(smoothing_param)
        else:
            raise Exception("Unknown method")

        if self.searcher is None:
            raise Exception("Searcher has not been created")
        self.searcher.setSimilarity(similarity)

    def open_writer(self):
        """Open IndexWriter."""
        if self.writer is None:
            config = IndexWriterConfig(self.get_version(), self.get_analyzer())
            config.setOpenMode(IndexWriterConfig.OpenMode.CREATE)
            self.writer = IndexWriter(self.dir, config)
        else:
            raise Exception("IndexWriter is already open")

    def close_writer(self):
        """Close IndexWriter."""
        if self.writer is not None:
            self.writer.close()
            self.writer = None
        else:
            raise Exception("There is no open IndexWriter to close")

    def add_document(self, contents):
        """
        Adds a Lucene document with the specified contents to the index.
        See LuceneDocument.create_document() for the explanation of contents.
        """
        if self.ldf is None:  # create a single LuceneDocument object that will be reused
            self.ldf = LuceneDocument()
        self.writer.addDocument(self.ldf.create_document(contents))

    def get_lucene_document_id(self, doc_id):
        """Loads a document from a Lucene index based on its id."""
        self.open_searcher()
        query = TermQuery(Term(self.FIELDNAME_ID, doc_id))
        tophit = self.searcher.search(query, 1).scoreDocs
        if len(tophit) == 1:
            return tophit[0].doc
        else:
            return None

    def get_document_id(self, lucene_doc_id):
        """Gets lucene document id and returns the document id."""
        self.open_reader()
        return self.reader.document(lucene_doc_id).get(self.FIELDNAME_ID)

    def print_document(self, lucene_doc_id, term_vect=False):
        """Prints document contents."""
        if lucene_doc_id is None:
            print "Document is not found in the index."
        else:
            doc = self.reader.document(lucene_doc_id)
            print "Document ID (field '" + self.FIELDNAME_ID + "'): " + doc.get(self.FIELDNAME_ID)

            # first collect (unique) field names
            fields = []
            for f in doc.getFields():
                if f.name() != self.FIELDNAME_ID and f.name() not in fields:
                    fields.append(f.name())

            for fname in fields:
                print fname
                for fv in doc.getValues(fname):  # printing (possibly multiple) field values
                    print "\t" + fv
                # term vector
                if term_vect:
                    print "-----"
                    termfreqs = self.get_doc_termfreqs(lucene_doc_id, fname)
                    for term in termfreqs:
                        print term + " : " + str(termfreqs[term])
                    print "-----"

    def get_lucene_query(self, query, field=FIELDNAME_CONTENTS):
        """Creates Lucene query from keyword query."""
        """
        @todo this is temp fix
        remove ( ) and !
        because they break QueryParser
        """
        query = query.replace("(", "").replace(")", "").replace("!", "")
        return QueryParser(self.get_version(), field,
                           self.get_analyzer()).parse(query)

    def analyze_query(self, query, field=FIELDNAME_CONTENTS):
        """
        Analyses the query and returns query terms

        :param field: field name
        :return: list of query terms
        """
        qterms = []  # holds a list of analyzed query terms
        ts = self.get_analyzer().tokenStream(field, query)
        term = ts.addAttribute(CharTermAttribute.class_)
        ts.reset()
        while ts.incrementToken():
            qterms.append(term.toString())
        ts.end()
        ts.close()
        return qterms

    def get_id_lookup_query(self, id, field=None):
        """Creates Lucene query for searching by (external) document id """
        if field is None:
            field = self.FIELDNAME_ID
        return TermQuery(Term(field, id))

    def get_and_query(self, queries):
        """Creates an AND Boolean query from multiple Lucene queries """
        # empty boolean query with Similarity.coord() disabled
        bq = BooleanQuery(False)
        for q in queries:
            bq.add(q, BooleanClause.Occur.MUST)
        return bq

    def get_or_query(self, queries):
        """Creates an OR Boolean query from multiple Lucene queries """
        # empty boolean query with Similarity.coord() disabled
        bq = BooleanQuery(False)
        for q in queries:
            bq.add(q, BooleanClause.Occur.SHOULD)
        return bq

    def get_phrase_query(self, query, field):
        """Creates phrase query for searching exact phrase."""
        phq = PhraseQuery()
        for t in query.split():
            phq.add(Term(field, t))
        return phq

    def get_id_filter(self):
        return FieldValueFilter(self.FIELDNAME_ID)

    def __to_retrieval_results(self, scoredocs, field_id=FIELDNAME_ID):
        """Convert Lucene scoreDocs results to RetrievalResults format."""
        rr = RetrievalResults()
        if scoredocs is not None:
            for i in xrange(len(scoredocs)):
                score = scoredocs[i].score
                lucene_doc_id = scoredocs[i].doc  # internal doc_id
                doc_id = self.reader.document(lucene_doc_id).get(field_id)
                rr.append(doc_id, score, lucene_doc_id)
        return rr

    def score_query(self, query, field_content=FIELDNAME_CONTENTS, field_id=FIELDNAME_ID, num_docs=100):
        """Score a given query and return results as a RetrievalScores object."""
        lucene_query = self.get_lucene_query(query, field_content)
        scoredocs = self.searcher.search(lucene_query, num_docs).scoreDocs
        return self.__to_retrieval_results(scoredocs, field_id)

    def num_docs(self):
        """Returns number of documents in the index."""
        self.open_reader()
        return self.reader.numDocs()

    def get_doc_termvector(self, lucene_doc_id, field):
        """Outputs the document term vector as a generator."""
        terms = self.reader.getTermVector(lucene_doc_id, field)
        if terms:
            termenum = terms.iterator(None)
            for bytesref in BytesRefIterator.cast_(termenum):
                yield bytesref.utf8ToString(), termenum

    def get_doc_termfreqs(self, lucene_doc_id, field):
        """Returns term frequencies for a given document field.

        :param lucene_doc_id: Lucene document ID
        :param field: document field
        :return dict: with terms
        """
        termfreqs = {}
        for term, termenum in self.get_doc_termvector(lucene_doc_id, field):
            termfreqs[term] = int(termenum.totalTermFreq())
        return termfreqs

    def get_doc_termfreqs_all_fields(self, lucene_doc_id):
        """
        Returns term frequency for all fields in the given document.

        :param lucene_doc_id: Lucene document ID
        :return: dictionary {field: {term: freq, ...}, ...}
        """
        doc_termfreqs = {}
        vectors = self.reader.getTermVectors(lucene_doc_id)
        if vectors:
            for field in vectors.iterator():
                doc_termfreqs[field] = {}
                terms = vectors.terms(field)
                if terms:
                    termenum = terms.iterator(None)
                    for bytesref in BytesRefIterator.cast_(termenum):
                        doc_termfreqs[field][bytesref.utf8ToString()] = int(termenum.totalTermFreq())
                    print doc_termfreqs[field]
        return doc_termfreqs


    # def get_doc_length(self, lucene_doc_id, field):
    #     """ Returns length of document for the given field."""
    #     # this returns -1, as the information is not saved in terms.
    #     terms = self.reader.getTermVector(lucene_doc_id, field)
    #     return terms.getSumTotalTermFreq()

    def get_coll_termvector(self, field):
        """ Returns collection term vector for the given field."""
        self.open_reader()
        fields = MultiFields.getFields(self.reader)
        if fields is not None:
            terms = fields.terms(field)
            if terms:
                termenum = terms.iterator(None)
                for bytesref in BytesRefIterator.cast_(termenum):
                    yield bytesref.utf8ToString(), termenum

    def get_coll_termfreq(self, term, field):
        """ Returns collection term frequency for the given field.

        :param term: string
        :param field: string, document field
        :return: int
        """
        self.open_reader()
        return self.reader.totalTermFreq(Term(field, term))

    def get_coll_length(self, field):
        """ Returns length of field in the collection.

        :param field: string, field name
        :return: int
        """
        self.open_reader()
        return self.reader.getSumTotalTermFreq(field)

    def get_avg_len(self, field):
        """ Return average length of a field in the collection.

        :param field: string, field name
        """
        self.open_reader()
        n = self.reader.getDocCount(field)  # number of documents with at least one term for this field
        len_all = self.reader.getSumTotalTermFreq(field)
        if n == 0:
            return 0
        else:
            return len_all / float(n)



class LuceneDocument(object):
    """Internal representation of a Lucene document"""

    def __init__(self):
        self.ldf = LuceneDocumentField()

    def create_document(self, contents):
        """Create a Lucene document from the specified contents.
        Contents is a list of fields to be indexed, represented as a dictionary
        with keys 'field_name', 'field_type', and 'field_value'."""
        doc = Document()
        for f in contents:
            doc.add(Field(f['field_name'], f['field_value'],
                          self.ldf.get_field(f['field_type'])))
        return doc


class LuceneDocumentField(object):
    """Internal handler class for possible field types"""

    def __init__(self):
        """Init possible field types"""

        # FIELD_ID: stored, indexed, non-tokenized
        self.field_id = FieldType()
        self.field_id.setIndexed(True)
        self.field_id.setStored(True)
        self.field_id.setTokenized(False)

        # FIELD_ID_TV: stored, indexed, not tokenized, with term vectors (without positions)
        # for storing IDs with term vector info
        self.field_id_tv = FieldType()
        self.field_id_tv.setIndexed(True)
        self.field_id_tv.setStored(True)
        self.field_id_tv.setTokenized(False)
        self.field_id_tv.setStoreTermVectors(True)

        # FIELD_TEXT: stored, indexed, tokenized, with positions
        self.field_text = FieldType()
        self.field_text.setIndexed(True)
        self.field_text.setStored(True)
        self.field_text.setTokenized(True)

        # FIELD_TEXT_TV: stored, indexed, tokenized, with term vectors (without positions)
        self.field_text_tv = FieldType()
        self.field_text_tv.setIndexed(True)
        self.field_text_tv.setStored(True)
        self.field_text_tv.setTokenized(True)
        self.field_text_tv.setStoreTermVectors(True)

        # FIELD_TEXT_TVP: stored, indexed, tokenized, with term vectors and positions
        # (but no character offsets)
        self.field_text_tvp = FieldType()
        self.field_text_tvp.setIndexed(True)
        self.field_text_tvp.setStored(True)
        self.field_text_tvp.setTokenized(True)
        self.field_text_tvp.setStoreTermVectors(True)
        self.field_text_tvp.setStoreTermVectorPositions(True)

    def get_field(self, type):
        """Get Lucene FieldType object for the corresponding internal FIELDTYPE_ value"""
        if type == Lucene.FIELDTYPE_ID:
            return self.field_id
        elif type == Lucene.FIELDTYPE_ID_TV:
            return self.field_id_tv
        elif type == Lucene.FIELDTYPE_TEXT:
            return self.field_text
        elif type == Lucene.FIELDTYPE_TEXT_TV:
            return self.field_text_tv
        elif type == Lucene.FIELDTYPE_TEXT_TVP:
            return self.field_text_tvp
        else:
            raise Exception("Unknown field type")


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--index", help="index directory", type=str)
    parser.add_argument("-l", "--lookup", help="lookup a document id", type=str)
    parser.add_argument("-t", "--termvect", help="term vector for a document id", type=str)
    parser.add_argument("-s", "--stat", help="stats", action="store_true", default=False)
    args = parser.parse_args()

    index_dir = args.index
    doc_id = args.lookup if args.lookup is not None else args.termvect

    print "Index:       " + index_dir + "\n"

    l = Lucene(index_dir, jvm_ram="8g") # use_ram=True)
    # print l.get_coll_termfreq("roman catholic", "contents")
    pq = l.get_phrase_query("originally used", "contents")#roman catholic ", "contents")
    # print l.get_coll_termfreq(pq.getTerms(), "contents")
    # print pq.toString()

    l.open_searcher()
    tophit = l.searcher.search(pq, 1).scoreDocs
    print tophit[0]#.doc

    if (args.lookup is not None) or (args.termvect is not None):
        lucene_doc_id = l.get_lucene_document_id(doc_id)
        tv = args.termvect is not None
        l.print_document(lucene_doc_id, tv)
        l.close_reader()
    elif args.stat:
        print "Number of documents: " + str(l.num_docs())


if __name__ == '__main__':
    main()