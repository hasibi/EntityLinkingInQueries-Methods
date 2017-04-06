"""
This a layer between scorer and Lucene index, which gives all the values needed for the scorer.

@author: Faegheh Hasibi
"""

from nordlys.retrieval.lucene_tools import Lucene


class IndexCache(Lucene):
    def __init__(self, index_dir, use_ram=False, jvm_ram=None, mongo_fields=None, cache_doc_freq=False):
        super(IndexCache, self).__init__(index_dir, use_ram=use_ram, jvm_ram=jvm_ram)
        self.n_docs = None
        self.mongo_fields = mongo_fields
        self.cache_doc_freq = cache_doc_freq  # If true, caches doc term freq
        # Caching variables
        self.doc_ids = dict()
        self.coll_termfreq = dict()
        self.doc_termfreq = dict()
        self.coll_length = dict()
        self.avg_len = dict()

    def num_docs(self):
        if self.n_docs is None:
            self.n_docs = super(IndexCache, self).num_docs()
        return self.n_docs

    def get_lucene_document_id(self, doc_id):
        """ Load a document from a Lucene index based on its id."""
        if doc_id not in self.doc_ids:
            self.doc_ids[doc_id] = super(IndexCache, self).get_lucene_document_id(doc_id)
        return self.doc_ids[doc_id]

    def get_doc_termfreqs(self, lucene_doc_id, field):
        """ 
        Returns term frequencies for a given document field.
        By default, doc termfreq is not cached.
        """
        if not self.cache_doc_freq:
            return super(IndexCache, self).get_doc_termfreqs(lucene_doc_id, field)
        else:
            if lucene_doc_id not in self.doc_termfreq:
                self.doc_termfreq[lucene_doc_id] = dict()
            if field not in self.doc_termfreq[lucene_doc_id]:
                self.doc_termfreq[lucene_doc_id][field] = dict()
                termfreqs = super(IndexCache, self).get_doc_termfreqs(lucene_doc_id, field)
                self.doc_termfreq[lucene_doc_id][field] = termfreqs
            return self.doc_termfreq[lucene_doc_id][field]

    def get_coll_termfreq(self, term, field):
        """Returns collection term frequency for the given field."""
        if field not in self.coll_termfreq:
            self.coll_termfreq[field] = dict()
        if term not in self.coll_termfreq[field]:
            self.coll_termfreq[field][term] = super(IndexCache, self).get_coll_termfreq(term, field)
        return self.coll_termfreq[field][term]

    def get_coll_length(self, field):
        """ Returns length of field in the collection. """
        if field not in self.coll_length:
            self.coll_length[field] = super(IndexCache, self).get_coll_length(field)
        return self.coll_length[field]

    def get_avg_len(self, field):
        """ Returns average length of the field in the collection. """
        if field not in self.avg_len:
            self.avg_len[field] = super(IndexCache, self).get_avg_len(field)
        return self.avg_len[field]

    def get_fields(self):
        """ Returns all field names. """
        if self.mongo_fields is not None:
            return self.mongo_fields.get_all()

    def get_field_count(self, field):
        """ Returns field count """
        if self.mongo_fields is not None:
            return self.mongo_fields.get_count(field)
