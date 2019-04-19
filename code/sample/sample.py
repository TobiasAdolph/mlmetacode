import re
import os
import json
import math
import random
import statistics

sampleType = "dmed" # dstat dmax dmin
sampleName = sampleType
base_dir = "/home/di72jiv/Documents/src/gerdi/ml/data"
srcDir  = os.path.join(base_dir, "dmax")
dataRegex = re.compile('[0-9]{2}\.data\.json$')
statFile = "statistic.json"


def getSizes(srcDir, dataRegex):
    sizes = []
    for f in [f for f in os.listdir(srcDir) if dataRegex.match(f)]:
        with open(os.path.join(srcDir, f), "r") as fp:
            sampleSpace = json.load(fp)
            sizes.append(len(sampleSpace))
    return sizes

if sampleType == "dstat":
    sampleSize = 1000
    sampleName = sampleType + str(sampleSize)
elif sampleType == "dmax":
    sampleSize = max(getSizes(srcDir, dataRegex))
elif sampleType == "dmin":
    sampleSize = min(getSizes(srcDir, dataRegex))
elif sampleType == "dmed":
    sampleSize = math.floor(statistics.median(getSizes(srcDir, dataRegex)))
    print(sampleSize)


tgtDir  = os.path.join(base_dir, sampleName)

try:
    os.stat(tgtDir)
except:
    os.mkdir(tgtDir)

stat = { "title": [], "description":  [], "tNd": [], "size" : {} } 

for f in [f for f in os.listdir(srcDir) if dataRegex.match(f)]:
    with open(os.path.join(srcDir, f), "r") as fp:
        sampleSpace = json.load(fp)
        stat["size"][f] = {"total": len(sampleSpace)}

        # TODO: shuffle test + eval
        # TODO: convert to input format
        sample = {}
        for key in random.sample(list(sampleSpace), min(sampleSize, len(sampleSpace))):
            sample[key] = sampleSpace[key]

        stat["size"][f]["sample"] = len(sample)

        for key, value in sample.items():
            stat["title"].append(
                    len(value["title"]))
            stat["description"].append(
                    len(value["description"]))
            stat["tNd"].append(
                    len(value["title"]) + len(value["description"]))

        # no need to sample dmax
        if not sampleType == "dmax":
            with open(os.path.join(tgtDir, f), "w") as wp:
                json.dump(sample, wp)

stat["titleMedian"] = statistics.median(stat["title"])
stat["descriptionMedian"] = statistics.median(stat["description"])
stat["tNdMedian"] = statistics.median(stat["tNd"])

del stat["title"]
del stat["description"]
del stat["tNd"]
with open(os.path.join(tgtDir, statFile), "w") as sf:
    json.dump(stat, sf)
