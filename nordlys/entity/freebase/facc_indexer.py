"""
Building an entities-only index from FACC-12.

@author: Faegheh Hasibi
@author: Krisztian Balog
"""
import os
from collections import defaultdict
import csv
from nordlys.retrieval.lucene_tools import Lucene


class FaccToLucene(object):

    def __init__(self, index_dir):
        self.index_dir = index_dir
        self.lucene = None

    def __start_indexing(self):
        self.lucene = Lucene(self.index_dir)
        self.lucene.open_writer()

    def __end_indexing(self):
        self.lucene.close_writer()

    def build_index(self, folder):
        """Builds the index for all docs in the folder."""
        self.__start_indexing()
        for chunk in sorted(os.listdir(folder)):
            path = folder + "/" + chunk
            if os.path.isdir(path):
                for dir in sorted(os.listdir(path)):
                    filedir = path + "/" + dir
                    for anns_file in sorted(os.listdir(filedir)):
                        self.index_file(filedir + "/" + anns_file)
        self.__end_indexing()

    def index_file(self, anns_file):
        """
        Builds index for a single file.

        :param anns_file: tsv annotation file
        """
        print "Indexing " + anns_file + "... ",

        with open(anns_file, 'rb') as tsvfile:
            reader = csv.reader(tsvfile, delimiter="\t", quoting=csv.QUOTE_NONE)
            file_dict = defaultdict(list)
            # Reads tsv lines
            for line in reader:
                doc_id, en = line[0], line[7]
                file_dict[doc_id].append(en)

        for doc_id, en_list in file_dict.iteritems():
            contents = self.__get_lucene_contents(doc_id, en_list)
            self.lucene.add_document(contents)

        print "done"

    def __get_lucene_contents(self, doc_id, en_list):
        """Adds the id and content field to the dpcument, to be indexed by Lucene."""
        contents = [{'field_name': Lucene.FIELDNAME_ID, 'field_value': doc_id, 'field_type': Lucene.FIELDTYPE_ID}]
        for en_id in en_list:
            contents.append({'field_name': "content", 'field_value': en_id, 'field_type': Lucene.FIELDTYPE_ID_TV})
        return contents


def main():
    index_dir = "/hdfs1/krisztib/facc-indices/clueweb12"
    facc_folder = "/hdfs1/krisztib/ClueWeb12-FACC1"
    FaccToLucene(index_dir).build_index(facc_folder)

if __name__ == "__main__":
    main()