import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import ijson
import json
import re
import util.util as util
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from cleanSchemeHelpers import getLabelFromScheme, getSchemeTester

def getLabel(config, subject, row):
    for scheme in config["clean"]["schemes"]:
        isScheme = getSchemeTester(scheme)
        if isScheme and isScheme(config, subject):
            return getLabelFromScheme(scheme, config, subject, row)
    return None

def getPayload(config, document):
    payload= {}
    for field in config["clean"]["dmode"].split("_"):
        fieldPlural = field + "s"
        payloadPart = ""
        if fieldPlural not in document.keys():
            continue
        for instance in document[fieldPlural]:
            if not instance["value"]:
                continue
            try:
                if not detect(instance["value"]) == "en":
                    continue
            except LangDetectException as e:
                continue
            payloadPart += " " + instance["value"]
        if len(payloadPart.split()) < config["clean"]["minLength"].get(field, 1):
            continue
        payload[field] = payloadPart
    return payload

def isSpecialChunk(config, fileName):
    if config["regex"]["special"].match(os.path.basename(fileName)):
        return True
    return False

def initResultRow(config):
    row = {
        "notAnnot": False,
        "multiAnnot": False,
        "notFit": False,
        "duplicate": False,
        "special": False,
        "useable": False,
        "schemeURI": set(),
        "subjectScheme": set(),
        "labels": set(),
        "payload": {},
        "payloadHash": None
    }
    for scheme in config["clean"]["schemes"]:
        row[scheme] = []
    return row

def finalizeRow(config, result, row):
    for field in ("schemeURI", "subjectScheme", "labels"):
        row[field] = list(row[field])
    for scheme in config["clean"]["schemes"]:
        row[scheme] = "|".join(row[scheme])
    result.append(row)

def processFile(instruction):
    config = instruction[0]
    filePath = instruction[1]
    fileName = os.path.basename(filePath)
    config["logger"].info("  Processing: {}".format(fileName))
    cleanId = config["regex"]["dataInput"].match(fileName).group(1)
    resultFile = os.path.join(
        config["clean"]["outputDir"],
        cleanId + ".chunk.json"
    )
    if os.path.isfile(resultFile):
        config["logger"].info("    {} already processed: {}".format(
            os.path.basename(fileName),
            resultFile
        ))
        return True
    try:
        with open(filePath) as f:
            result = []
            docCounter = 0
            for document in ijson.items(f, 'documents.item'):
                row = initResultRow(config)
                if isSpecialChunk(config, fileName):
                    row["id"] = fileName + "_" + str(docCounter)
                    row["labels"].add(config["specialDict"][fileName])
                    row["special"] = True
                    docCounter += 1
                else: # metadata should be DataCite compliant
                    row["id"] = document["identifier"]["value"]
                    for subject in document["subjects"]:
                        if "schemeURI" in subject.keys():
                            row["schemeURI"].add(subject["schemeURI"])
                        if "subjectScheme" in subject.keys():
                            row["subjectScheme"].add(subject["subjectScheme"])
                        label = getLabel(config, subject, row)
                        if not label:
                            continue
                        row["labels"].add(label)
                if not row["labels"]:
                    row["notAnnot"] = True
                    finalizeRow(config, result, row)
                    continue
                if len(row["labels"]) != 1:
                    row["multiAnnot"] = True
                    finalizeRow(config, result, row)
                    continue

                payload = getPayload(config, document)
                if not len(payload) == len(config["clean"]["dmode"].split("_")):
                    row["payloadNotFit"] = True

                row["useable"] = True
                row["payload"] = payload
                row["payloadHash"] = util.getDictHash(payload)
                finalizeRow(config, result, row)

        config["logger"].info("    Save results for: {} ({} documents)".format(cleanId, len(result)))
        with open(resultFile, "w") as f:
            json.dump(result, f)
        return True
    except Exception as e:
        config["logger"].error(
            "Failure in processing file {}: {} {} {} {}".format(
                fileName,
                sys.exc_info()[-1].tb_lineno,
                e.__class__,
                e.__doc__,
                e
            )
        )
        raise
