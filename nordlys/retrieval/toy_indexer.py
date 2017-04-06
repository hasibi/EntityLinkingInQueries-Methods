"""
Toy indexer example.

@author: Krisztian Balog
"""

import sys
from lucene_tools import Lucene


def main(argv):

    index_dir = "./data/toy_index"

    docs = [
        {'id': 1,
         'title': "Rap God",
         'content': "Look, I was gonna go easy on you and not to hurt your feelings"
        },
        {'id': 2,
         'title': "Lose Yourself",
         'content': "Yo, if you could just, for one minute Or one split second in time, forget everything Everything that bothers you, or your problems Everything, and follow me"
        },
        {'id': 3,
         'title': "Love The Way You Lie",
         'content': "Just gonna stand there and watch me burn But that's alright, because I like the way it hurts"
        },
        {'id': 4,
         'title': "The Monster",
         'content': "I'm friends with the monster That's under my bed Get along with the voices inside of my head"
        },
        {'id': 5,
         'title': "Beautiful",
         'content': "Lately I've been hard to reach I've been too long on my own Everybody has a private world Where they can be alone"
        }
    ]

    lucene = Lucene(index_dir)
    print index_dir
    lucene.open_writer()

    for doc in docs:
        contents = []
        print "Indexing document ID " + str(doc['id'])
        # make "catchall" field manually
        doc[Lucene.FIELDNAME_CONTENTS] = doc['title'] + " " + doc['content']
        for f in doc:
            field_name = Lucene.FIELDNAME_ID if f == "id" else f
            field_type = Lucene.FIELDTYPE_ID if f == "id" else Lucene.FIELDTYPE_TEXT_TVP
            contents.append({'field_name': field_name,
                             'field_value': str(doc[f]),
                             'field_type': field_type})
        lucene.add_document(contents)

    lucene.close_writer()


if __name__ == '__main__':
    main(sys.argv[1:])
