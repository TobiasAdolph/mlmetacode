import json
import os
from collections import OrderedDict

dmode="all"
dtype="dmax"
dpath="../data"
statisticsFile = os.path.join(dpath, dtype, "statistic.json")
evalFile = os.path.join(dpath, dtype, "{}_{}_mlp_model_eval.json".format(dtype, dmode))
anzsrcFile = "anzsrc.json"

with open (statisticsFile, "r") as sf:
    data = json.load(sf)

with open (evalFile, "r") as ef:
    evalData = json.load(ef)

with open (anzsrcFile, "r") as af:
    anzsrc = json.load(af)

dd = OrderedDict(sorted(data["size"].items(), key=lambda x: x[1]["sample"]))
pad = len(str(list(dd.values())[-1]["sample"]))

discPad = len(evalData['0']["name"])
for key, value in evalData.items():
    if len(value["name"]) > discPad:
        discPad = len(value["name"])

def getDiscName(key):
    key = key.split(".")[0]
    return anzsrc["{0:2}".format(key)]

def getSens(key):
    key = key.split(".")[0]
    return evalData[str(int(key)-1)]["sens"]

def getSpec(key):
    key = key.split(".")[0]
    return evalData[str(int(key)-1)]["spec"]

print("{};{};{};{}".format(
    "Discipline",
    "records",
    "sensivity",
    "specificity"
))


for key, value in dd.items():
    print("{};{};{};{}".format(
        getDiscName(key),
        value["sample"],
        getSens(key),
        getSpec(key),
))
