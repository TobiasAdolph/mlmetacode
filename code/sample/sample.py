import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import json
import math
import random
import re
import statistics
import util.util as util

def prepare():
    parser = argparse.ArgumentParser(
        description='RETRIEVE: retrieve all raw data.'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'sample'")
    parser.add_argument('--type',
            default = "dmax",
            choices = ["min", "med", "max", "static"],
            help = "Mode to sample, if static, you must specify --maxsize")
    parser.add_argument('--maxsize',
            default = 1000,
            help = "Maximum size of the sample for each label, only with type: static")

    args = parser.parse_args()
    config = util.loadConfig(args.config)
    config["type"] = args.type
    config["size"] = args.maxsize
    config["logger"] = util.setupLogging(config, "sample")
    return config

def getSizes(config):
    sizes = []
    for f in os.listdir(config["clean"]["outputDir"]):
        print(f)
        if re.match(config["sample"]["dataInputRegex"], f):
            with open(os.path.join(config["clean"]["outputDir"], f), "r") as fp:
                sampleSpace = json.load(fp)
                sizes.append(len(sampleSpace))
    return sizes

if __name__ == "__main__":
    config = prepare()
    config["logger"].info(
        "Starting retrieve with config {}".format(config["sample"]["hash"])
    )
    if config["type"] == "dmax":
        config["size"] = max(getSizes(srcDir, dataRegex))
    elif config["type"] == "dmin":
        config["size"] = min(getSizes(srcDir, dataRegex))
    elif config["type"] == "dmed":
        config["size"] = math.floor(statistics.median(getSizes(srcDir, dataRegex)))

    config["logger"].info("\tMode: {}\n\tSize: {}".format(config["type"],
                                                          config["size"]))

    result = {
        "title": [],
        "description":  [],
        "tNd": [],
        "size" : {}
    }

    for f in os.listdir(config["clean"]["outputDir"]):
        if re.match(config["sample"]["dataInputRegex"], f):
            with open(os.path.join(config["clean"]["outputDir"], f), "r") as fp:
                sampleSpace = json.load(fp)
            result["size"][f] = {"total": len(sampleSpace)}
            sample = {}
            sampleKeys = random.sample(
                list(sampleSpace),
                min(config["size"], len(sampleSpace))
            )
            for key in sampleKeys:
                sample[key] = sampleSpace[key]

            result["size"][f]["sample"] = len(sample)

            for key, value in sample.items():
                result["title"].append(len(value["title"]))
                result["description"].append(len(value["description"]))
                result["tNd"].append(len(value["title"]) + len(value["description"]))

            with open(os.path.join(config["sample"]["outputDir"], f), "w") as fp:
                json.dump(sample, fp)

    result["titleMedian"] = statistics.median(result["title"])
    result["descriptionMedian"] = statistics.median(result["description"])
    result["tNdMedian"] = statistics.median(result["tNd"])
    del result["title"]
    del result["description"]
    del result["tNd"]
    for key in ("titleMedian", "descriptionMedian", "tNdMedian"):
        config["logger"].info("{}: {}".format(key, result[key]))

    with open(os.path.join(config["sample"]["outputDir"], "statistics.json"), "w") as f:
        json.dump(result, f)
