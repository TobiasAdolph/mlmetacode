import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import glob
import json
import re
import util.util as util
import cleanHelpers
import pandas as pd

from concurrent.futures import ProcessPoolExecutor
from langdetect.detector_factory import init_factory

def prepare():
    """ Prepares a cleaning run

    # Returns
        config: dict A configuration with all paths, compiled regexes and a
                     logger
    """
    parser = argparse.ArgumentParser(
        description='CLEAN retrieved metadata records'
    )

    parser.add_argument('--config',
            required    = True,
            help        ="File with the configuration for the cleaning run")
    parser.add_argument('--worker',
            default    =  3,
            help        ="Number of workers")
    args = parser.parse_args()

    config = util.loadConfig(args.config)
    config["worker"] = int(args.worker)

    config["labels"]  = util.getLabels(config)

    with open(os.path.join(
        config["base"]["configDir"],
        "specialDataProviders.json"), "r") as f:
        config["specialDict"]  = json.load(f)

    config["regex"] = {
        "ddcValue": re.compile(config["clean"]["regex"]["ddcValue"]),
        "ddcSchemeURI": re.compile(config["clean"]["regex"]["ddcSchemeURI"]),
        "special": re.compile(config["clean"]["regex"]["special"]),
        "dataInput": re.compile(config["clean"]["regex"]["dataInput"]),
        "dataOutput": re.compile(config["clean"]["regex"]["dataOutput"])
    }
    for static in config["clean"]["static"]:
        config["regex"][static["name"]] = re.compile(static["regex"])

    config["logger"] = util.setupLogging(config, "clean")
    return config

def divide(config):
    config["logger"].info("Starting {} workers".format(config["worker"]))

    files = []
    for f in glob.glob(
        os.path.join(config["retrieve"]["baseDir"], config["clean"]["retrieveHash"]) + "/*"):
        if config["regex"]["dataInput"].match(f):
            files.append(f)
    files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    workpackage = [(config, f) for f in files]

    config["logger"].info("  Will process {} files".format(len(files)))

    #workpackage = [workpackage[-35], workpackage[-25], workpackage[-16]]

    with ProcessPoolExecutor(
        max_workers = config["worker"],
        initializer = init_factory
    ) as ex:
        res = zip(workpackage, ex.map(cleanHelpers.processFile, workpackage))

    for r in res:
        if not r[1]:
            config["logger"].warning("Unsuccesful run for {}".format(r[0][1]))

def conquer(config):
    config["logger"].info("Combining worker output")
    statisticsFields = set([
        "notAnnot",
        "multiAnnot",
        "notFit",
        "duplicate",
        "special",
        "useable",
        "id",
        "labels"
    ])
    statisticsFields.update(config["clean"]["schemes"])
    statistics = []

    result = {
        "subjectScheme": {},
        "schemeURI": {},
        "payload" : {}
    }

    for label in range(len(util.getLabels(config))):
        result["payload"][label] = {}

    files = []
    for f in glob.glob(config["clean"]["outputDir"] + "/*"):
        if config["regex"]["dataOutput"].match(f):
            files.append(f)

    for f in files:
        with open(f, "r") as fh:
            rows = json.load(fh)
        for row in rows:
            if row["useable"]:
                if len(row["labels"]) != 1:
                    raise Error("{} in {} is useable, but has more than 1 label".format(
                        row["id"], f))
                label = row["labels"][0]
                if row["payloadHash"] in result["payload"][label].keys():
                    row["duplicate"] = True
                    row["useable"] = False
                else:
                    result["payload"][label][row["payloadHash"]] = row["payload"]

            statistic = {}
            for field in statisticsFields:
                statistic[field] = row[field]
            statistics.append(statistic)

            for field in ("subjectScheme", "schemeURI"):
                for fieldInstance in row[field]:
                    result[field][fieldInstance] = (
                        result[field].get(fieldInstance, 0) + 1)
    statistics = pd.DataFrame(statistics)

    for key in result["payload"].keys():
        dumpFile = os.path.join(config["clean"]["outputDir"], str(key) + ".data.json")
        with open(dumpFile, "w") as f:
            json.dump(result["payload"][key], f)

    for key in ("subjectScheme", "schemeURI"):
        dumpFile = os.path.join(config["clean"]["outputDir"], key + ".json")
        with open(dumpFile, "w") as f:
            json.dump(result[key], f)

    with open(os.path.join(config["clean"]["outputDir"], "statistics.csv"), "w") as f:
        statistics.to_csv(f)

    # Print results to log + on stdout
    config["logger"].info("Discipline match after data cleanup")
    longestLabelName = max(len(label) for label in config["labels"])
    for label in sorted(result["payload"].keys()):
        labelSize = len(result["payload"][label])
        config["logger"].info("  {:<{longestLabelName}}: {:>8}".format(
            config["labels"][label],
            labelSize,
            longestLabelName=longestLabelName))
    config["logger"].info("General Statistics:")
    printInfos = (
        "duplicate",
        "notAnnot",
        "multiAnnot",
        "notFit",
        "useable"
    )
    longestPrintInfo = max(len(v) for v in printInfos)
    for printInfo in printInfos:
        config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            printInfo, sum(statistics[printInfo]), longestPrintInfo=longestPrintInfo))

    config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            "Documents", len(statistics), longestPrintInfo=longestPrintInfo))

    config["logger"].info("")

    for scheme in config["clean"]["schemes"]:
        config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            scheme, sum((statistics[scheme] != "") & (statistics["useable"])), longestPrintInfo=longestPrintInfo))
    config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
        "special", sum((statistics["special"]) & (statistics["useable"])), longestPrintInfo=longestPrintInfo))
    config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            "Useable", sum(statistics["useable"]), longestPrintInfo=longestPrintInfo))

    for scheme in config["clean"]["schemes"]:
        config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            scheme,
            sum((statistics[scheme] == "") & (statistics["useable"])),
            longestPrintInfo=longestPrintInfo))

if __name__ == "__main__":
    config = prepare()
    print("Starting with config {}".format(config["clean"]["hash"]))
    config["logger"].info("Starting clean with config {}".format(
        config["clean"]["hash"])
    )
    divide(config)
    conquer(config)
