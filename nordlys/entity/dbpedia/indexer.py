"""
Creates a Lucene index for DBpedia from MongoDB.

- URI values are resolved using a simple heuristic
- fields are indexed as multi-valued
- catch-all fields are not indexed with positions, other fields are

@author: Krisztian Balog
@author: Faegheh Hasibi
"""

import sys
from urllib import unquote

from nordlys import config
from nordlys.retrieval.mongo_fields import Fields
from nordlys.storage.mongo import Mongo
from nordlys.retrieval.lucene_tools import Lucene
from nordlys.entity.config import COLLECTION_DBPEDIA


class MongoDBToLucene(object):
    def __init__(self, host=config.MONGO_HOST, db=config.MONGO_DB, collection=COLLECTION_DBPEDIA):
        self.mongo = Mongo(host, db, collection)
        self.contents = None

    def __resolve_uri(self, uri):
        """Resolves the URI using a simple heuristic."""
        uri = unquote(uri)  # decode percent encoding
        if uri.startswith("<") and uri.endswith(">"):
            # Part between last ':' and '>', and _ replaced with space.
            # Works fine for <dbpedia:XXX> and <dbpedia:Category:YYY>
            return uri[uri.rfind(":") + 1:-1].replace("_", " ")
        else:
            return uri

    def __is_uri(self, value):
        """ Returns true if the value is uri. """
        if value.startswith("<dbpedia:") and value.endswith(">"): # and (not value.startswith("<dbpedia:Category:")):
            return True
        return False

    def __get_field_value(self, value, only_uris=False):
        """Converts mongoDB field value to indexable values by resolving URIs.
        It may be a string or a list and the return value is of the same data type."""
        if type(value) is list:
            nval = []  # holds resolved values
            for v in value:
                if not only_uris:
                    nval.append(self.__resolve_uri(v))
                elif only_uris and self.__is_uri(v):
                    nval.append(v)
            return nval
        else:
            if not only_uris:
                return self.__resolve_uri(value)
            elif only_uris and self.__is_uri(value):
                return value
            # return self.__resolve_uri(value) if only_uris else value
        return None

    def __add_to_contents(self, field_name, field_value, field_type):
        """Adds field to document contents.
        Field value can be a list, where each item is added separately (i.e., the field is multi-valued).
        """
        if type(field_value) is list:
            for fv in field_value:
                self.__add_to_contents(field_name, fv, field_type)
        else:
            if len(field_value) > 0:  # ignore empty fields
                self.contents.append({'field_name': field_name,
                                      'field_value': field_value,
                                      'field_type': field_type})

    def build_index(self, index_config, only_uris=False):
        """Builds index.

        :param index_config: index configuration
        """
        lucene = Lucene(index_config['index_dir'])
        lucene.open_writer()

        fieldtype_tv = Lucene.FIELDTYPE_ID_TV if only_uris else Lucene.FIELDTYPE_TEXT_TV
        fieldtype_tvp = Lucene.FIELDTYPE_ID_TV if only_uris else Lucene.FIELDTYPE_TEXT_TVP

        # iterate through MongoDB contents
        i = 0
        for mdoc in self.mongo.find_all():

            # this is just to speed up things a bit
            # we can skip the document right away if the ID does not start
            # with "<dbpedia:"
            if not mdoc[Mongo.ID_FIELD].startswith("<dbpedia:"):
                continue

            # get back document from mongo with keys and _id field unescaped
            doc = self.mongo.get_doc(mdoc)

            # check must_have fields
            skip_doc = False
            for f, v in index_config['fields'].iteritems():
                if ("must_have" in v) and (v['must_have']) and (f not in doc):
                    skip_doc = True
                    break

            if skip_doc:
                continue

            # doc contents is represented as a list of fields
            # (mind that fields are multi-valued)
            self.contents = []

            # each predicate to a separate field
            for f in doc:
                if f == Mongo.ID_FIELD:  # id is special
                    self.__add_to_contents(Lucene.FIELDNAME_ID, doc[f], Lucene.FIELDTYPE_ID)
                if f in index_config['ignore']:
                    pass
                else:
                    # get resolved field value(s) -- note that it might be a list
                    field_value = self.__get_field_value(doc[f], only_uris)
                    # ignore empty fields
                    if (field_value is None) or (field_value == []):
                        continue

                    to_catchall_content = True if index_config['catchall_all'] else False

                    if f in index_config['fields']:
                        self.__add_to_contents(f, field_value, fieldtype_tvp)

                        # fields in index_config['fields'] are always added to catch-all content
                        to_catchall_content = True

                        # copy field value to other field(s)
                        # (copying is without term positions)
                        if "copy_to" in index_config['fields'][f]:
                            for f2 in index_config['fields'][f]['copy_to']:
                                self.__add_to_contents(f2, field_value, fieldtype_tv)

                    # copy field value to catch-all content field
                    # (copying is without term positions)
                    if to_catchall_content:
                        self.__add_to_contents(Lucene.FIELDNAME_CONTENTS, field_value, fieldtype_tv)

            # add document to index
            lucene.add_document(self.contents)

            i += 1
            if i % 1000 == 0:
                print str(i / 1000) + "K documents indexed"

        # close Lucene index
        lucene.close_writer()

        print "Finished indexing (" + str(i) + " documents in total)"


def main(argv):
    # title + short abstract
    """
    index_config0 = {'index_dir' : "/hdfs1/krisztib/dbpedia-3.9-indices/index0",
                     'fields' : {'<rdfs:label>' : {'must_have' : True}, 
                                 '<rdfs:comment>': {'must_have' : True}
                                 }
                     }
    """

    # title, short abstract, long abstract, wikilinks, wikipedia categories
    """
    index_config1 = {'index_dir': "/hdfs1/krisztib/dbpedia-3.9-indices/index1",
                     'fields': {'<rdfs:label>': {'must_have': True},
                                '<rdfs:comment>': {'must_have': True},
                                '<dbo:abstract>': {},
                                '<dbo:wikiPageWikiLink>': {},
                                '<dcterms:subject>': {}
                     }
    }
    """

    # all DBpedia fields, except those containing only links (YAGO types, link to WP page, sameAs FB)
    # catch-all fields 'names' and 'types'
    """index_config2 = {'index_dir': "/hdfs1/krisztib/dbpedia-3.9-indices/index2",
                     'fields': {'<rdfs:label>': {'must_have': True, 'copy_to': ["names"]},
                                '<foaf:name>': {'copy_to': ["names"]},
                                '<rdf:type>': {'copy_to': ["types"]},
                                '<rdfs:comment>': {'must_have': True},
                                '<dbo:abstract>': {},
                                '<dcterms:subject>': {'copy_to': ["types"]},
                                '<dbo:wikiPageWikiLink>': {},
                                '!<dbo:wikiPageRedirects>': {'copy_to': ["names"]}
                     },
                     'catchall_all': True,  # index all fields in catch-all content (otherwise only those listed above)
                     'ignore': ["yago:<rdf:type>", "<foaf:isPrimaryTopicOf>", "<owl:sameAs>"]  # except these
    }"""

    fields = {}
    top_fields = Fields().get_all()
    for f in top_fields:
        if f == "<rdfs:label>":
            fields[f] = {'must_have': True, 'copy_to': ["names"]}
        elif (f == "<foaf:name>") or (f == "!<dbo:wikiPageRedirects>"):
            fields[f] = {'copy_to': ["names"]}
        elif (f == "<rdf:type>") or (f == "<dcterms:subject>"):
            fields[f] = {'copy_to': ["types"]}
        elif f == "<rdfs:comment>":
            fields[f] = {'must_have': True}
        else:
            fields[f] = {}


    # Similar to index2
    # index_config6 = {'index_dir': "/home/faeghehh/dbpedia-3.9-indices/index6",
    #                  'fields': fields,
    #                  'catchall_all': True,
    #                  'ignore': ["yago:<rdf:type>", "<foaf:isPrimaryTopicOf>", "<owl:sameAs>"]  # except these
    #                 }


    # Similar to index6, ignore fields are changed
    index_config7 = {'index_dir': "/home/faeghehh/dbpedia-3.9-indices/index7",
                     'fields': fields,
                     'catchall_all': True,
                     'ignore': ["<owl:sameAs>"]  # except these
                    }

    # Similar to index7, but keeps only uris
    index_config7_only_uri = {'index_dir': "/hdfs1/krisztib/dbpedia-3.9-indices/index7_only_uri",
                     'fields': fields,
                     'catchall_all': True,
                     'ignore': ["<owl:sameAs>"]  # except these
                    }

    print "index dir: " + index_config7_only_uri['index_dir']
    m2l = MongoDBToLucene()
    m2l.build_index(index_config7_only_uri, only_uris=True)
    print "index build" + index_config7_only_uri['index_dir']


if __name__ == "__main__":
    main(sys.argv[1:])
