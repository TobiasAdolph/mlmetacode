import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import glob
import json
import logging
import re
import util.util as util
import cleanHelpers

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

    config["anzsrcDict"]  = util.getAnzsrc(config)
    with open(os.path.join(
        config["base"]["configDir"],
        "specialDataProviders.json"), "r") as f:
        config["specialDict"]  = json.load(f)

    config["regex"] = {
        "ddcValue": re.compile('(^\d+\.\d+,)+'),
        "jelSubjectScheme": re.compile('^JEL.*'),
        "special": re.compile(config["clean"]["sregex"]),
        "dataInput": re.compile(config["clean"]["dataInputRegex"]),
        "dataOutput": re.compile(config["clean"]["dataOutputRegex"])
    }

    config["logger"] = util.setupLogging(config, "clean")
    return config

def divide(config):
    config["logger"].info("Starting {} workers".format(config["worker"]))

    files = []
    for f in glob.glob(
        os.path.join(config["retrieve"]["outputDir"], "..", config["clean"]["retrieveHash"]) + "/*"):
        if config["regex"]["dataInput"].match(f):
            files.append(f)
    files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    workpackage = [(config, f) for f in files]

    config["logger"].info("  Will process {} files".format(len(files)))

    with ProcessPoolExecutor(
        max_workers = config["worker"],
        initializer = init_factory
    ) as ex:
        res = zip(workpackage, ex.map(cleanHelpers.processFile, workpackage))

    for r in res:
        if r[1]:
            config["logger"].debug("Success for {}: {}".format(r[0][1], r[1]))
        else:
            config["logger"].warning("Unsuccesful run for {}".format(r[0][1]))

def conquer(config):
    config["logger"].info("Combining worker output")
    results = cleanHelpers.init_result(config)

    files = []
    for f in glob.glob(config["clean"]["outputDir"] + "/*"):
        if config["regex"]["dataOutput"].match(f):
            files.append(f)

    for f in files:
        with open(f, "r") as fh:
            result = json.load(fh)
            results["documents"] += result["documents"]
            results["notAnnotatable"] += result["notAnnotatable"]
            results["multiAnnotations"] += result["multiAnnotations"]
            results["payloadNotFit"] += result["payloadNotFit"]
            results["duplicates"] += result["duplicates"]

        for label in result["payload"].keys():
            results["payload"][label] = results["payload"].get(label, {})
            for payloadHash in result["payload"][label].keys():
                if payloadHash in results["payload"][label].keys():
                    results["duplicates"] += 1
                results["payload"][label][payloadHash] = result["payload"][label][payloadHash]

        for label in result["anzsrc2subject"].keys():
            for key, value in result["anzsrc2subject"][label].items():
                results["anzsrc2subject"][label][key] = (
                    results["anzsrc2subject"][label].get(key, 0) + value )

        for label, value in result["special"].items():
            results["special"][label] += value

        for key, value in result["subjectSchemes"].items():
            results["subjectSchemes"][key] = results["subjectSchemes"].get(key, 0) + value

        for key, value in result["schemeURIs"].items():
            results["schemeURIs"][key] = results["schemeURIs"].get(key, 0) + value

    for key in results["payload"].keys():
        dumpFile = os.path.join(config["clean"]["outputDir"], key + ".data.json")
        with open(dumpFile, "w") as f:
            json.dump(results["payload"][key], f)

    for key in ("special", "subjectSchemes", "schemeURIs", "anzsrc2subject"):
        dumpFile = os.path.join(config["clean"]["outputDir"], key + ".json")
        with open(dumpFile, "w") as f:
            json.dump(results[key], f)

    # Print results to log + on stdout
    config["logger"].info("Discipline match after data cleanup")
    longestCategoryName = max(len(v) for k,v in config["anzsrcDict"].items())
    for category in sorted(results["payload"].keys()):
        categorySize = len(results["payload"][category])
        results["useableDocuments"] += categorySize
        config["logger"].info("  {:<{longestCategoryName}}: {:>8} ({:>5} special)".format(
            config["anzsrcDict"][category],
            categorySize,
            results["special"][category],
            longestCategoryName=longestCategoryName))
    config["logger"].info("General Statistics:")
    printInfos = (
        "duplicates",
        "notAnnotatable",
        "multiAnnotations",
        "payloadNotFit",
        "useableDocuments",
        "documents"
    )
    longestPrintInfo = max(len(v) for v in printInfos)
    for printInfo in printInfos:
        config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            printInfo, results[printInfo], longestPrintInfo=longestPrintInfo))

if __name__ == "__main__":
    config = prepare()
    config["logger"].info("Starting clean with config {}".format(
        config["clean"]["hash"])
    )
    divide(config)
    conquer(config)
