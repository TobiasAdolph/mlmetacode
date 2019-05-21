import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import ijson
import json
import re
import util.util as util
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from cleanDataHelpers import ddcNames, mappingDDC

def isANZSRC(subject):
    if "schemeURI" not in subject.keys():
        return False
    if (subject["schemeURI"] == "http://www.abs.gov.au/ausstats"
            "/abs@.nsf/0/6BB427AB9696C225CA2574180004463E"):
        return True
    return False

def isDDC(config, subject):
    if "subjectScheme" not in subject.keys():
        return False
    if config["regex"]["ddcValue"].match(subject["value"].strip()):
        return False
    if subject["subjectScheme"] in ddcNames:
        return True
    return False

def isJEL(config, subject):
    if "subjectScheme" not in subject.keys():
        return False
    if config["regex"]["jelSubjectScheme"].match(subject["subjectScheme"]):
        return True
    else:
        return False

def registerMapping(anzsrc, payload, anzsrc2subject):
    if anzsrc not in anzsrc2subject.keys():
        anzsrc2subject[anzsrc] = { payload: 1, "total": 1}
    elif payload not in anzsrc2subject[anzsrc].keys():
        anzsrc2subject[anzsrc][payload] = 1
        anzsrc2subject[anzsrc]["total"] += 1
    else:
        anzsrc2subject[anzsrc][payload] += 1
        anzsrc2subject[anzsrc]["total"] += 1

def getBaseAnzsrc(config, subject):
    payload = subject["value"].lower().strip()
    if isDDC(config, subject):
        for pair in mappingDDC:
            anzsrc = pair[0]
            regex  = pair[1]
            if regex.match(payload):
                return anzsrc
    elif isANZSRC(subject):
        anzsrcNumber = re.search('\d+', payload).group()
        if len(anzsrcNumber) % 2 == 0:
            anzsrcKey = payload[:2]
        else:
            anzsrcKey = "0" + payload[:1]

        if anzsrcKey in config["anzsrcDict"].keys():
            anzsrc = config["anzsrcDict"][anzsrcKey]
        else:
            anzsrc = config["anzsrcDict"]["00"]
        return anzsrc
    elif isJEL(config, subject):
        anzsrc = config["anzsrcDict"]["14"]
        return anzsrc
    return ""

def getMinLength(field):
    if field == "description":
        return 15
    return 1

def getPayload(config, document):
    payload= {}
    for field in config["dmode"].split("_"):
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
                config["logger"].debug("Cannot process {}: {}".format(instance["value"],e))
                continue
            payloadPart += " " + instance["value"]
        if len(payloadPart.split()) < getMinLength(field):
            continue
        payload[field] = payloadPart
    return payload

def isSpecialChunk(config, fileName):
    if config["regex"]["special"].match(os.path.basename(fileName)):
        return True
    return False

def getLabels(config, document, result, fileName):
    seenSchemeURIs = []
    seenSubjectSchemes = []
    labels = set()

    if isSpecialChunk(config, fileName):
        lookup = os.path.basename(fileName)
        label = config["anzsrcDict"][config["specialDict"][lookup]][:2]
        labels.add(label)
    else:
        for subject in document["subjects"]:
            # count the documents with this schemeURI (once)
            if "schemeURI" in subject.keys():
                schemeURI = subject["schemeURI"]
                if schemeURI not in seenSchemeURIs:
                    seenSchemeURIs.append(schemeURI)
                    result["schemeURIs"][schemeURI] = (
                        result["schemeURIs"].get(schemeURI, 0) + 1)
            # count the documents with this subjectScheme (once)
            if "subjectScheme" in subject.keys():
                subjectScheme = subject["subjectScheme"]
                if subjectScheme not in seenSchemeURIs:
                    seenSchemeURIs.append(subjectScheme)
                    result["subjectSchemes"][subjectScheme] = (
                        result["subjectSchemes"].get(subjectScheme, 0) + 1)
            # add to label if fitting
            anzsrc = getBaseAnzsrc(config, subject)
            if not anzsrc:
                continue

            registerMapping(anzsrc,
                            subject["value"],
                            result["anzsrc2subject"])
            labels.add(anzsrc[:2].strip())
    return labels

def init_result(config):
    result = {
        "documents" : 0,
        "notAnnotatable": 0,
        "multiAnnotations": 0,
        "payloadNotFit": 0,
        "useableDocuments": 0,
        "schemeURIs" : {},
        "special" : {},
        "subjectSchemes" : {},
        "anzsrc2subject" : {},
        "payload" : {},
    }

    for label in config["anzsrcDict"]:
        result["anzsrc2subject"][config["anzsrcDict"][label]] = {"total": 0}
        result["special"][label] = 0
        result["payload"][label] = {}

    return result


def processFile(instruction):
    config = instruction[0]
    fileName = instruction[1]
    config["logger"].info("  Processing: {}".format(fileName))
    resultFile = os.path.join(
        config["processedDataDir"],
        "clean",
        "chunks",
        os.path.basename(fileName)
    )
    if os.path.isfile(resultFile):
        config["logger"].info("    {} already processed: {}".format(
            fileName,
            resultFile
        ))
        return True

    with open(fileName) as f:
        result = init_result(config)
        for document in ijson.items(f, 'documents.item'):
            result["documents"] += 1
            labels = getLabels(config, document, result, fileName)
            if not labels:
                result["notAnnotatable"] += 1
                continue
            elif len(labels) != 1:
                result["multiAnnotations"] += 1
                continue
            label = labels.pop()
            payload = getPayload(config, document)

            if not len(payload) == len(config["dmode"].split("_")):
                result["payloadNotFit"] += 1
                continue
            payloadHash = util.getDictHash(payload)
            result["payload"][label][payloadHash] = payload
            if isSpecialChunk(config, fileName):
                result["special"][label] += 1
    config["logger"].info("    Save results for: {}".format(resultFile))
    with open(resultFile, "w") as f:
        json.dump(result, f)
    return True
