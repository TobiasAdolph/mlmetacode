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
        description='Clean retrieved metadata records'
    )

    parser.add_argument('--config',
            required    = True,
            help        ="File with the configuration for the cleaning run")
    parser.add_argument('--worker',
            default    =  3,
            help        ="Number of workers")
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print("{} is not a path to a file".format(args.config))
    config = util.loadConfig(args.config)
    config["worker"] = int(args.worker)

    config["anzsrcDict"]  = util.getAnzsrc(config)
    with open(os.path.join(
        config["configDir"],
        "specialDataProviders.json"), "r") as f:
        config["specialDict"]  = json.load(f)

    config["regex"] = {
        "ddcValue": re.compile('(^\d+\.\d+,)+'),
        "jelSubjectScheme": re.compile('^JEL.*'),
        "special": re.compile(config["sregex"]),
        "data": re.compile(config["dregex"])
    }

    config["chunksDir"] = os.path.join(config["processedDataDir"], "clean", "chunks")

    if not os.path.isdir(config["chunksDir"]):
        os.mkdir(config["chunksDir"])


    # LOGGING
    logger = logging.getLogger('clean')
    config["logger"] = logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(os.path.join(config["logDir"], 'clean.log'))
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s|%(process)d %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info("Starting clean with config {}".format(config["hash"]))
    return config

def divide(config):
    config["logger"].info("Starting {} workers".format(config["worker"]))

    files = []
    for f in glob.glob(config["rawDataDir"] + "/*"):
        if config["regex"]["data"].match(f):
            files.append(f)
    files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    files = [(config, f) for f in files]

    config["logger"].info("  Will process {} files".format(len(files)))

    with ProcessPoolExecutor(
        max_workers = config["worker"],
        initializer = init_factory
    ) as ex:
        res = zip(files, ex.map(cleanHelpers.processFile, files))

    for r in res:
        if r[1]:
            config["logger"].debug("Success for {}: {}".format(r[0][1], r[1]))
        else:
            config["logger"].warn("Unsuccesful run for {}".format(r[0][1]))

def conquer(config):
    config["logger"].info("Combining worker output")
    results = cleanHelpers.init_result(config)

    files = []
    for f in glob.glob(config["chunksDir"] + "/*"):
        if config["regex"]["data"].match(f):
            files.append(f)

    for f in files:
        with open(f, "r") as fh:
            result = json.load(fh)
            results["documents"] += result["documents"]
            results["notAnnotatable"] += result["notAnnotatable"]
            results["multiAnnotations"] += result["multiAnnotations"]
            results["payloadNotFit"] += result["payloadNotFit"]

        for label in result["payload"].keys():
            results["payload"][label] = results["payload"].get(label, {})
            for payloadHash in result["payload"][label].keys():
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
        dumpFile = os.path.join(config["processedDataDir"], "clean", key + ".data.json")
        with open(dumpFile, "w") as f:
            json.dump(results["payload"][key], f)

    for key in results.keys():
        if key not in ("payload"):
            dumpFile = os.path.join(config["processedDataDir"], "clean", key + ".data.json")
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
    divide(config)
    conquer(config)
