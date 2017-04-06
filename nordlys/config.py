"""
Global nordlys config.

@author: Krisztian Balog
"""

from os import path

NORDLYS_DIR = path.dirname(path.abspath(__file__))
DATA_DIR = path.dirname(path.dirname(path.abspath(__file__))) + "/data"
LIB_DIR = path.dirname(path.dirname(path.abspath(__file__))) + "/lib"

MONGO_DB = "nordlys"
MONGO_HOST = "localhost"
# MONGO_HOST = "mongodb://dascosa02.idi.ntnu.no:27017/"
