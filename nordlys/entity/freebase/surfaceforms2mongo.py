"""
Adds entity surface forms from the Freebase Annotated ClueWeb Corpora (FACC).

The input to this script is (name variant, Freebase entity, count) triples.
See `data/facc1/README.md` for the preparation of FACC data in such format.

@author: Krisztian Balog
"""

import argparse
import os

from nordlys.entity.surfaceforms import SurfaceForms
from utils import FreebaseUtils


class FACCSurfaceForms(SurfaceForms):

    def __init__(self, predicate, lowercase=False):
        """Constructor.

        Args:
            predicate: predicate used for storing surface forms (facc09 or facc12)
            lowercase: whether to lowercase surface forms
        """
        super(FACCSurfaceForms, self).__init__(lowercase)
        self.predicate = predicate

    def __add_surface_form(self, surface_form, freebase_id, count):
        """Adds a surface form."""
        if self.lowercase:
            surface_form = surface_form.lower()
        # translate freebase_id to prefixed URI
        entity_uri = FreebaseUtils.freebase_id_to_uri(freebase_id)
        # increase count
        self.inc(surface_form, self.predicate, entity_uri, count)

    def __add_file(self, tsv_filename):
        """Adds name variants from an FACC tsv file."""
        print "Adding name variants from '" + tsv_filename + "'..."
        infile = open(tsv_filename, "r")
        for line in infile:
            f = line.rstrip().split("\t")
            self.__add_surface_form(f[0], f[1], int(f[2]))
        infile.close()

    def add_dir(self, basedir):
        """Adds FACC annotations from a directory recursively."""
        for path, dirs, files in os.walk(basedir):
            for fn in files:
                if fn.endswith(".tsv"):
                    self.__add_file(os.path.join(path, fn))

         
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="Command (only add_dir is supported ATM)", choices=['add_dir'])
    parser.add_argument("dir", help="Path to directory to be added (with .tsv files)")
    parser.add_argument("predicate", help="Predicate for storing data", choices=['facc09', 'facc12'])
    parser.add_argument("-l", "--lowercase", help="Lowercased", action="store_true", dest="lower", default=False)
    args = parser.parse_args()

    if args.command == "add_dir":
        fsf = FACCSurfaceForms(args.predicate, args.lower)
        fsf.add_dir(args.dir)

if __name__ == "__main__":
    main()