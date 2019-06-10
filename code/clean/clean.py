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
import gc
from concurrent.futures import ProcessPoolExecutor
from langdetect.detector_factory import init_factory
from langdetect import DetectorFactory

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
    print("Starting with config {}".format(config["clean"]["hash"]))
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
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    config["labels"]  = util.getLabels(config)


    if config["clean"]["stemming"] == "porter":
        config["stemmer"] = PorterStemmer()
    if config["clean"]["stemming"] == "lancaster":
        config["stemmer"] = LancasterStemmer()

    config["regex"] = {
        "ddcValue": re.compile(config["clean"]["regex"]["ddcValue"]),
        "ddcSchemeURI": re.compile(config["clean"]["regex"]["ddcSchemeURI"]),
        "special": re.compile(config["clean"]["regex"]["special"]),
        "dataInput": re.compile(config["clean"]["regex"]["dataInput"]),
        "dataOutput": re.compile(config["clean"]["regex"]["dataOutput"])
    }

    config["replace"] = {}
    for regex, replacement in config["clean"]["replace"].items():
        config["replace"][replacement] = re.compile(regex)
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

    #workpackage = [workpackage[-55], workpackage[-75], workpackage[-86]]

    DetectorFactory.seed = config["clean"]["seed"]
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
        "notAnnot",
        "multiAnnot",
        "notFit",
        "duplicate",
        "special",
        "useable",
        "id",
        "payload"
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
                if len(row["labels"]) != 1:
                    raise Error("{} in {} is useable, but has more than 1 label".format(
                        row["id"], f))
                label = row["labels"][0]
                # Check for duplicates
                if row["payloadHash"] in useablePayloadHashes.keys():
                    for alreadyInHash in useablePayloadHashes[row["payloadHash"]]:
                        row["duplicate"] = True
                        row["useable"] = False
                useablePayloadHashes[row["payloadHash"]] = useablePayloadHashes.get(row["payloadHash"], [])
                useablePayloadHashes[row["payloadHash"]].append(row["payload"])

            # fill the result row for the data frame
            resultRow = {}
            for label in range(1, len(config["labels"])):
                resultRow[str(label)] = False
                if label in row["labels"]:
                    resultRow[str(label)] = True

            for field in resultFields:
                resultRow[field] = row[field]

            result.append(resultRow)

            for field in ("subjectScheme", "schemeURI"):
                for fieldInstance in row[field]:
                    statistics[field][fieldInstance] = (
                        statistics[field].get(fieldInstance, 0) + 1)

    resultDf = pd.DataFrame(result)
    del result
    gc.collect()

    getStat = {
        "notAnnot": 0,
        "multiAnnot": 0,
        "notFit": 0,
        "duplicate": 0,
        "useable": 0
    }
    for printInfo in getStat.keys():
        getStat[printInfo] = sum(resultDf[printInfo])

    getStat["total"] = len(resultDf)
    store = pd.HDFStore(os.path.join(config["clean"]["outputDir"], "result.h5"))
    store["r"] = resultDf
    resultU= resultDf[resultDf.useable].copy()
    del resultDf
    store.close()
    gc.collect()

    for key in ("subjectScheme", "schemeURI"):
        dumpFile = os.path.join(config["clean"]["outputDir"], key + ".json")
        with open(dumpFile, "w") as f:
            json.dump(statistics[key], f)

    # Print results to log + on stdout
    config["logger"].info("Discipline match after data cleanup")
    formatString = "{:>5}: {:>8} {:>7} {:>7}"
    headers = ["Label", "Total", "Special", "MultiS"]
    for scheme in config["clean"]["schemes"]:
        formatString += " {:>7}"
        headers.append(scheme)
    config["logger"].info(formatString.format(*headers))

    totalMultiSchemes = 0
    for label in range(1, len(config["labels"])):
        labelSize = len(resultU[resultU[str(label)]])
        labelSpecial = len(resultU[(resultU.special) & (resultU[str(label)])])
        labelSchemes = []
        for scheme in config["clean"]["schemes"]:
            labelSchemes.append(
                len(resultU[
                        (resultU[scheme] != "") &
                        (resultU[str(label)]
                    )]
                )
            )
        labelMultiSchemes = sum(labelSchemes) + labelSpecial - labelSize
        totalMultiSchemes += labelMultiSchemes
        config["logger"].info(formatString.format(
            label,
            labelSize,
            labelSpecial,
            labelMultiSchemes,
            *labelSchemes
        ))
    totalSchemes = []
    for scheme in config["clean"]["schemes"]:
        totalSchemes.append(len(resultU[resultU[scheme] != ""]))
    config["logger"].info(formatString.format(
            "all",
            len(resultU),
            len(resultU[resultU["special"]]),
            totalMultiSchemes,
            *totalSchemes
        ))

    config["logger"].info("General Statistics:")

    longestPrintInfo = max(len(k) for k in getStat.keys())
    for printInfo in getStat.keys():
        config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            printInfo, getStat[printInfo], longestPrintInfo=longestPrintInfo))

    store = pd.HDFStore(os.path.join(config["clean"]["outputDir"], "useable.h5"))
    store["r"] = resultU
    store.close()

if __name__ == "__main__":
    config = prepare()
    config["logger"].info("Starting clean with config {}".format(
        config["clean"]["hash"])
    )
    divide(config)
    conquer(config)
