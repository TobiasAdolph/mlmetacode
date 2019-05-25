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
        description='SAMPLE: sample from cleaned data.'
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
    config["size"] = int(args.maxsize)
    config["logger"] = util.setupLogging(config, "sample")
    config["src"] = os.path.join(
        config["clean"]["outputDir"],
        "..",
        config["sample"]["cleanHash"]
    )
    return config

def getSizes(config):
    sizes = []
    for f in os.listdir(config["src"]):
        if re.match(config["sample"]["dataInputRegex"], f):
            with open(os.path.join(config["src"], f), "r") as fp:
                sampleSpace = json.load(fp)
                sizes.append(len(sampleSpace))
    return sizes

if __name__ == "__main__":
    config = prepare()
    config["logger"].info(
        "Starting sample with config {}".format(config["sample"]["hash"])
    )
    if config["type"] == "max":
        config["size"] = max(getSizes(config))
    elif config["type"] == "min":
        config["size"] = min(getSizes(config))
    elif config["type"] == "med":
        config["size"] = math.floor(statistics.median(getSizes(config)))
    else:
        config["type"] += str(config["size"])

    if not os.path.isdir(os.path.join(config["sample"]["outputDir"],
                                 config["type"])):
        os.makedirs(os.path.join(config["sample"]["outputDir"], config["type"]))

    config["logger"].info("\tMode: {}\n\tSize: {}".format(config["type"],
                                                          config["size"]))

    result = {
        "title": [],
        "description":  [],
        "tNd": [],
        "size" : {}
    }

    for f in os.listdir(config["src"]):
        if re.match(config["sample"]["dataInputRegex"], f):
            with open(os.path.join(config["src"], f), "r") as fp:
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

            with open(os.path.join( config["sample"]["outputDir"], config["type"], f), "w") as fp:
                json.dump(sample, fp)

    result["titleMedian"] = statistics.median(result["title"])
    result["descriptionMedian"] = statistics.median(result["description"])
    result["tNdMedian"] = statistics.median(result["tNd"])
    del result["title"]
    del result["description"]
    del result["tNd"]
    for key in ("titleMedian", "descriptionMedian", "tNdMedian"):
        config["logger"].info("{}: {}".format(key, result[key]))

    with open(os.path.join(config["sample"]["outputDir"], config["type"], "statistics.json"), "w") as f:
        json.dump(result, f)
