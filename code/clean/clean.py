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
    statisticsFields = set([
        "notAnnot",
        "multiAnnot",
        "notFit",
        "duplicate",
        "duplicateId",
        "special",
        "useable",
        "id"
    ])
    statisticsFields.update(config["clean"]["schemes"])

    result = {
        "subjectScheme": {},
        "schemeURI"    : {}
    }
    useablePayloadHashes = {}
    statistics    = []

    files = []
    for f in glob.glob(config["clean"]["outputDir"] + "/*"):
        if config["regex"]["dataOutput"].match(f):
            files.append(f)

    for f in files:
        with open(f, "r") as fh:
            rows = json.load(fh)
        for row in rows:
            row["duplicateId"] = ""
            if row["useable"]:
                if len(row["labels"]) != 1:
                    raise Error("{} in {} is useable, but has more than 1 label".format(
                        row["id"], f))
                label = row["labels"][0]
                if row["payloadHash"] in useablePayloadHashes.keys():
                    for alreadyInHash in useablePayloadHashes[row["payloadHash"]]:
                        if alreadyInHash["payload"]["description"] == row["payload"]["description"]:
                            row["duplicateId"] = alreadyInHash["id"]
                            row["duplicate"] = True
                            row["useable"] = False
                            break
                        else:
                            config["logger"].info(
                                "{} and {} have the same hash, but differ in content".format(
                                    alreadyInHash["id"], row["id"]
                                )
                            )
                useablePayloadHashes[row["payloadHash"]] = useablePayloadHashes.get(row["payloadHash"], [])

                useablePayloadHashes[row["payloadHash"]].append(row)
            statistic = {}
            for label in range(1, len(config["labels"])):
                statistic[str(label)] = False
                if label in row["labels"]:
                    statistic[str(label)] = True

            for field in statisticsFields:
                statistic[field] = row[field]
            statistics.append(statistic)

            for field in ("subjectScheme", "schemeURI"):
                for fieldInstance in row[field]:
                    result[field][fieldInstance] = (
                        result[field].get(fieldInstance, 0) + 1)

    payload = {}
    for payloadHash, payloadHashArray in useablePayloadHashes.items():
        for p in payloadHashArray:
            label = p["labels"][0]
            payload[label] = payload.get(label, [])
            payload[label].append(p["payload"])

    statistics = pd.DataFrame(statistics)
    store = pd.HDFStore(os.path.join(config["clean"]["outputDir"], "stat.h5"))
    store['statistics'] = statistics

    for label in payload.keys():
        dumpFile = os.path.join(config["clean"]["outputDir"], str(label) + ".data.json")
        with open(dumpFile, "w") as f:
            json.dump(payload[label], f)

    for key in ("subjectScheme", "schemeURI"):
        dumpFile = os.path.join(config["clean"]["outputDir"], key + ".json")
        with open(dumpFile, "w") as f:
            json.dump(result[key], f)

    # Print results to log + on stdout
    config["logger"].info("Discipline match after data cleanup")
    formatString = "{:>5}: {:>8} {:>7} {:>7}"
    headers = ["Label", "Total", "Special", "MultiS"]
    for scheme in config["clean"]["schemes"]:
        formatString += " {:>7}"
        headers.append(scheme)
    config["logger"].info(formatString.format(*headers))
    statisticsU = statistics[statistics.useable]
    totalMultiSchemes = 0
    for label in sorted(payload.keys()):
        if label < 1:
            continue
        labelSize = len(statisticsU[statisticsU[str(label)]])
        labelSpecial = len(statisticsU[(statisticsU.special) & (statisticsU[str(label)])])
        labelSchemes = []
        for scheme in config["clean"]["schemes"]:
            labelSchemes.append(
                len(statisticsU[
                        (statisticsU[scheme] != "") &
                        (statisticsU[str(label)]
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
        totalSchemes.append(len(statisticsU[statisticsU[scheme] != ""]))
    config["logger"].info(formatString.format(
            "all",
            len(statisticsU),
            len(statisticsU[statisticsU["special"]]),
            totalMultiSchemes,
            *totalSchemes
        ))


    config["logger"].info("General Statistics:")
    printInfos = (
        "notAnnot",
         "multiAnnot",
         "notFit",
         "duplicate",
         "useable"
    )

    longestPrintInfo = max(len(v) for v in printInfos)
    for printInfo in printInfos:
        config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            printInfo, sum(statistics[printInfo]), longestPrintInfo=longestPrintInfo))

    config["logger"].info("  {:<{longestPrintInfo}}: {:>9}".format(
            "Documents", len(statistics), longestPrintInfo=longestPrintInfo))

if __name__ == "__main__":
    config = prepare()
    config["logger"].info("Starting clean with config {}".format(
        config["clean"]["hash"])
    )
    divide(config)
    conquer(config)
