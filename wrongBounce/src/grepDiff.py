import argparse
import os.path
import re
from difflib import SequenceMatcher

class matchBlockObject:
    """Object containing a string block represetning matched config and a list of devices which have it present"""
    def __init__(self, matchblock, devicename):
        self.matchblock = matchblock
        self.devicename = devicename


def argparser():
    """ Returns an argparser instance (argparse.ArgumentParser) to support command line options."""
    parser = argparse.ArgumentParser(description='Arguments for using script')
    parser.add_argument('-s', '--search',
                        required=True,
                        action='store',
                        help='search term')
    parser.add_argument('-c', '--configdir',
                        required=True,
                        action='store',
                        help='Config directory')

    return parser

def diffTheFiles(new_file, old_file):
    """ returns True if the files are the same"""
    s = SequenceMatcher(None, new_file, old_file)

    return s.ratio() == 1


def storeMatchBlock(mboList, matchblock, devicename):
    createnew = True

    for obj in mboList:
        if diffTheFiles(matchblock, obj.matchblock):
            obj.devicename.append(devicename)
            createnew = False

    if createnew:
        mbo = matchBlockObject(matchblock, [devicename])
        mboList.append(mbo)


def printTheMBO(mboList) :
    for obj in mboList:
        print("--------------------")
        print(obj.devicename)
        print(obj.matchblock)


if __name__ == "__main__":
    parser = argparser()
    args = parser.parse_args()

    searchterm = args.search
    configdir = args.configdir

    matchBlockObjectList = []

    for filename in os.listdir(configdir):
        if os.path.splitext(filename)[1] == "":
            file = open(configdir + filename, 'r')
            stringmatches = ""

            matchfound = False

            for line in file:
                if matchfound:
                    if line[0:1] == " ":
                        stringmatches += line
                    else:
                        matchfound = False

                if re.search(searchterm, line):
                    stringmatches +=line
                    matchfound = True

            storeMatchBlock(matchBlockObjectList, stringmatches, os.path.basename(filename))
        else:
            print("Ignoring file {0}".format(os.path.basename(filename)))

    printTheMBO(matchBlockObjectList)