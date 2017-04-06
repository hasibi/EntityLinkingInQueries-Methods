"""
Collects entity name variants from DBpedia.

Entity name variants are stored in a mongoDB collection, with
name variant as the key. The value part contains predicate-URI 
pairs; i.e., we know from the predicate where the mapping comes
from. For example,
{ 
  "_id" : "NYT", 
  "<dbo:wikiPageRedirects>" : [ "<dbpedia:The_New_York_Times>" ] 
}

NOTE: 
- We assume that each entity URI in DBpedia has a single <rdfs:label>
relation and redirects to at most one URI. In practice, there is a few entities 
with multiple <rdfs:label>, but with the same object value, in DBpedia 3.9. 
check_multi_labels() is used to list and fix those.
- There can be multiple entity names via the <foaf:name> relation and we
use all of them. So the previous thing done with <rdfs:label> is probably
not necessary anymore...

@author: Krisztian Balog
"""

import sys
from nordlys.config import MONGO_DB, MONGO_HOST
from nordlys.storage.mongo import Mongo
from config import *

class DBPediaNameVariants(object):

    def __init__(self):
        self.mongo_dbpedia = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_DBPEDIA)
        self.mongo_nv = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_DBPEDIA_NV)

    def check_multi_labels(self, predicate="<rdfs:label>", fix=False):
        """Check entities with multiple predicate attributes.
        
        Args:
            fix: False only lists them; 
                 True replaces the list with its first element (which is the 
                 same as the other elements in practice -- at least for DBpedia 3.9)
        """
        for mdoc in self.mongo_dbpedia.find_all():
            if predicate not in mdoc: continue
            if type(mdoc[predicate]) is list:
                doc = self.mongo_dbpedia.get_doc(mdoc)
                print doc[predicate]
                if fix:
                    label = doc[predicate][0]
                    self.mongo_dbpedia.add(doc[Mongo.ID_FIELD],
                                              {predicate : label})
                    print "Replaced with label: '" + label + "'"

    def __store_variants(self, uri, rel, name, case_sensitive=True):
        """Store a given name variant."""
        # if case-insensitive, lowercase name
        if not self.case_sensitive: 
            name = name.lower()
                        
        # append {rel: uri} to name string
        self.mongo_nv.append_list(name, rel, uri)

    def drop(self):
        """Drop the collection."""
        self.mongo_nv.drop()

    def build(self, predicate="<rdfs:label>", case_sensitive=False):
        """Build the name variants collection."""
                
        # iterate through mongoDB contents
        i = 0
        for mdoc in self.mongo_dbpedia.find_all():
            
            # check if entity has the given predicate
            if predicate not in mdoc: continue
            
            # get back document from mongo with keys and _id field unescaped
            doc = self.mongo_dbpedia.get_doc(mdoc)
            
            name = doc[predicate]
            # skip empty names
            if len(name) == 0: continue

            # determine the uri it should point to and the rel by which
            # the name is connected to the uri
                        
            # if it's a redirect page
            if "<dbo:wikiPageRedirects>" in doc:
                rel = "<dbo:wikiPageRedirects>" 
                uri = doc[rel]
            else: # it's one or more string label(s)
                rel = predicate
                uri = doc[Mongo.ID_FIELD]
            
            if isinstance(name, list): # list of names
                for n in name:
                    self.__store_variants(uri, rel, n, case_sensitive)
            else: # single name
                self.__store_variants(uri, rel, name, case_sensitive)
        
            i+=1
            if i % 1000 == 0: 
                print str(i / 1000) + "K documents indexed"


    
def main(argv): 
    # Building -- @todo need to check
    #nv = DBPediaNameVariants()
    #nv.drop()
    #nv.build("<rdfs:label>", case_sensitive=False)
    #nv.build("<foaf:name>", case_sensitive=False)    
    #nv.check_multi_labels("<rdfs:label>", fix=True)
    
    # Lookup is a static method
    mongo_nv = Mongo(MONGO_HOST, MONGO_DB, COLLECTION_DBPEDIA_NV)
    print DBPediaNameVariants.lookup(mongo_nv, "new york")
        
if __name__ == "__main__":
    main(sys.argv[1:])