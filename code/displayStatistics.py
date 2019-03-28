import json
from collections import OrderedDict

statisticsFile = "../data/dmax/statistic.json"
anzsrcFile = "anzsrc.json"

with open (statisticsFile, "r") as sf:
    data = json.load(sf)

with open (anzsrcFile, "r") as af:
    anzsrc = json.load(af)


dd = OrderedDict(sorted(data["size"].items(), key=lambda x: x[1]["sample"]))
import pprint
pad = len(str(list(dd.values())[-1]["sample"]))


def getDiscName(key):
    
    key = key.split(".")[0]
    return anzsrc["{0:2}".format(key)]


for key, value in dd.items():
    print("{}: {:{pad}}".format(getDiscName(key), value["sample"], pad=pad))

