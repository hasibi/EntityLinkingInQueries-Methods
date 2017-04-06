"""
erd global econfig

"""

from os import path
from nordlys.wikipedia.config import COLLECTION_SURFACEFORMS_WIKI_2015, COLLECTION_SURFACEFORMS_WIKI_2010, \
    COLLECTION_SURFACEFORMS_WIKI_2012
from nordlys.entity.entity import Entity
from nordlys.entity.surfaceforms import SurfaceForms
from nordlys.erd.features.facc_feat import FACCFeat
from nordlys.retrieval.index_cache import IndexCache

# ------- Directories -------
DATA_DIR = path.dirname(path.dirname(path.dirname(path.abspath(__file__)))) + "/data/erd"

# output dirs
OUTPUT_DIR = path.dirname(path.dirname(path.dirname(path.abspath(__file__)))) + "/output"
MODEL_DIR = OUTPUT_DIR + "/models"
RES_DIR = OUTPUT_DIR + "/res"
EVAL_DIR = OUTPUT_DIR + "/eval"

# ------- Index Path -------
INDEX_DIR = "/data/dbpedia-3.9-indices/index7"
FACC_INDEX = "/data/facc-indices/clueweb12"

# ------- Entity predicates -------
IREDIRECT = "!<dbo:wikiPageRedirects>"  # Inverse Redirect
REDIRECT = "<dbo:wikiPageRedirects>"
TITLE = "<rdfs:label>"
WIKILINKS = "<dbo:wikiPageWikiLink>"
SHORT_ABS = "<rdfs:comment>"
LONG_ABS = "<dbo:abstract>"
CATEGORIES = "<dcterms:subject>"

# ------- Variables -------
def load_kb():
    # Freebase and Wiki ids of proper noun entities.
    print "Loading knowledge base snapshot ..."
    FB_DBP_FILE = DATA_DIR + "/fb_dbp_snapshot.txt"
    __fb_dbp_file = open(FB_DBP_FILE, "r")
    global KB_SNP_DBP, KB_SNP_FB
    for line in __fb_dbp_file:
        cols = line.strip().split("\t")
        # KB_SNP_DBP.add(cols[1])
        KB_SNP_FB.add(cols[0])
    __fb_dbp_file.close()

KB_SNP_DBP = set()
KB_SNP_FB = set()
load_kb()

LUCENE = IndexCache(INDEX_DIR)
print "INDEX:" + INDEX_DIR

FACC_LUCENE = IndexCache(FACC_INDEX)
FACC_FEAT = FACCFeat(FACC_LUCENE)
ENTITY = Entity()
SF = SurfaceForms(lowercase=True)


