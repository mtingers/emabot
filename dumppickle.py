import pickle
import sys
from pprint import pprint

with open(sys.argv[1], 'rb') as fd:
    data = pickle.load(fd)
    pprint(data)
