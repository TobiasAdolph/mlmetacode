import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import glob
import json
import re
import util.util as util
import hashlib
import cleanHelpers
import pandas as pd
import numpy as np
import gc
from concurrent.futures import ProcessPoolExecutor
from langdetect.detector_factory import init_factory
from langdetect import DetectorFactory

"""
    The script is divided in three parts:
        1. prepare:
           sets up the cleaning process according to config and cli-params
        2. divide:
           starts cleaning the retrieved chunks in worker processes
        3. conquer:
           combines the worker output
    Each of the parts corresponds to a function in this file
"""

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
    # This should be the only output, allowing to tail the log
    config["logger"] = util.setupLogging(config, "clean")
    config["worker"] = int(args.worker)

    usedMappingHash = util.getFileHash("clean/cleanDataHelpers.py")
    if usedMappingHash != config["clean"]["mappingHash"]:
        config["logger"].error("Hash of used and configured mapping differ:"
                               "\n\t{} (used)"
                               "\n\t{} (configured)"
                               "\n\tRestore old mapping or change config".format(
                                   usedMappingHash,
                                   config["clean"]["mappingHash"]
                               )
        )
        os.sys.exit(1)
    config["labels"]  = util.getLabels(config)

    config["regex"] = {
        "ddcValue": re.compile(config["clean"]["regex"]["ddcValue"]),
        "ddcSchemeURI": re.compile(config["clean"]["regex"]["ddcSchemeURI"]),
        "special": re.compile(config["clean"]["regex"]["special"]),
        "dataInput": re.compile(config["clean"]["regex"]["dataInput"]),
        "dataOutput": re.compile(config["clean"]["regex"]["dataOutput"])
    }

    return config

def divide(config):
    config["logger"].info("Starting {} workers".format(config["worker"]))
    DetectorFactory.seed = config["clean"]["seed"]

    files = []
    for f in glob.glob(
        os.path.join(config["retrieve"]["baseDir"], config["clean"]["retrieveHash"]) + "/*"):
        if config["regex"]["dataInput"].match(f):
            files.append(f)
    # Sort the files in decreasing order of size will result in a better
    # distribution of work.
    files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    # Add the config to each file, so workers know about the config
    workpackage = [(config, f) for f in files]
    # Debug:
    # workpackage = [workpackage[-10], workpackage[-12], workpackage[-34], workpackage[-100]]
    config["logger"].info("  Will process {} files".format(len(files)))

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
    resultFields = set([
        "duplicate",
        "id",
        "multiAnnot",
        "notAnnot",
        "notFit",
        "special",
        "useable",
        "labels"
    ])
    resultFields.update(config["clean"]["schemes"])

    statistics= {
        "subjectScheme": {},
        "schemeURI"    : {}
    }
    useablePayloadHashes = {}
    result    = []

    files = []
    for f in glob.glob(config["clean"]["outputDir"] + "/*"):
        if config["regex"]["dataOutput"].match(f):
            files.append(f)

    for f in files:
        with open(f, "r") as fh:
            rows = json.load(fh)
        for row in rows:
            if row["useable"]:
                # Check for duplicates
                if row["payloadHash"] in useablePayloadHashes.keys():
                    for alreadyInHash in useablePayloadHashes[row["payloadHash"]]:
                        row["duplicate"] = True
                        row["useable"] = False
                useablePayloadHashes[row["payloadHash"]] = (
                    useablePayloadHashes.get(row["payloadHash"], []))
                useablePayloadHashes[row["payloadHash"]].append(row["payload"])

            # fill the result row for the data frame
            resultRow = {}
            for field in resultFields:
                resultRow[field] = row[field]
            # put each payload field in a separate row
            for key in config["clean"]["payloadFields"]:
                resultRow[key] = row["payload"][key]

            result.append(resultRow)

            for field in ("subjectScheme", "schemeURI"):
                for fieldInstance in row[field]:
                    statistics[field][fieldInstance] = (
                        statistics[field].get(fieldInstance, 0) + 1)
    df = pd.DataFrame(result)
    del result
    gc.collect()
    udf = df[df.useable].copy()
    df.to_csv(
        os.path.join(config["clean"]["outputDir"], "result.csv")
    )
    del df
    gc.collect()
    udf.to_csv(
        os.path.join(config["clean"]["outputDir"], "useable.csv")
    )

    for key in ("subjectScheme", "schemeURI"):
        dumpFile = os.path.join(config["clean"]["outputDir"], key + ".json")
        with open(dumpFile, "w") as f:
            json.dump(statistics[key], f)


if __name__ == "__main__":
    config = prepare()
    print("Starting with config {}\n\ttail -f {}".format(
        config["clean"]["hash"],
        config["clean"]["logFile"]
    ))
    config["logger"].info("Starting clean with config {}".format(
        config["clean"]["hash"])
    )
    divide(config)
    conquer(config)
