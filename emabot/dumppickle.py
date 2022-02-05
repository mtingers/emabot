import pickle
import sys
from pprint import pprint

def main():
    if len(sys.argv) != 2:
        print('usage: {} <pickle-file-path>'.format(sys.argv[0]))
        sys.exit(1)
    with open(sys.argv[1], 'rb') as fd:
        data = pickle.load(fd)
        pprint(data)

if __name__ == '__main__':
    main()
