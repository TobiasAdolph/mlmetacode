import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import glob
import json
import logging
import re
import util.util as util
from cleanDataHelpers import ddcNames, mappingDDC
from concurrent.futures import ProcessPoolExecutor
from langdetect import detect
from langdetect.detector_factory import init_factory
from langdetect.lang_detect_exception import LangDetectException

################################################################################
# CONFIGURATION
################################################################################
parser = argparse.ArgumentParser(
    description='Clean retrieved metadata records'
)

parser.add_argument('--config',
        required    = True,
        help        ="File with the configuration for the cleaning run")
args = parser.parse_args()

if not os.path.isfile(args.config):
    print("{} is not a path to a file".format(args.config))

config = util.loadConfig(args.config)
anzsrcDict  = util.getAnzsrc(config)
with open(os.path.join(
    config["configDir"],
    "specialDataProviders.json"), "r") as f:
    specialDict  = json.load(f)

########################################
# LOGGING
########################################
logger = logging.getLogger('clean')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.join(config["logDir"], 'clean.log'))
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s|%(asctime)s -- %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.info("Startin cleanRetrievedRecords with config {}".format(config["hash"]))

################################################################################
# FUNCTIONS
################################################################################
def isANZSRC(subject):
    if "schemeURI" not in subject.keys():
        return False
    if (subject["schemeURI"] == "http://www.abs.gov.au/ausstats"
            "/abs@.nsf/0/6BB427AB9696C225CA2574180004463E"):
        return True
    return False

def isDDC(subject):
    if "subjectScheme" not in subject.keys():
        return False
    coordinateRegex = re.compile('(^\d+\.\d+,)+')
    if coordinateRegex.match(subject["value"].strip()):
        return False
    if subject["subjectScheme"] in ddcNames:
        return True
    return False

def isJEL(subject):
    if "subjectScheme" not in subject.keys():
        return False
    if re.match(r'^JEL.*', subject["subjectScheme"]):
        return True
    else:
        return False

def isAnnotatable(subject):
    if isDDC(subject) or isJEL(subject) or isANZSRC(subject):
        if re.match(r'^[a-zA-Z0-9].*', subject["value"]):
            return True
    return False

def getEnglishValueOrEmpty(field, document):
    if field in document.keys():
        for instance in document[field]:
            if not instance["value"] or len(instance["value"].split()) < 7:
                continue
            if detect(instance["value"]) == "en":
                return instance["value"]
    return ""

def registerMapping(anzsrc, payload, anzsrc2subject):
    if anzsrc not in anzsrc2subject.keys():
        anzsrc2subject[anzsrc] = { payload: 1, "total": 1}
    elif payload not in anzsrc2subject[anzsrc].keys():
        anzsrc2subject[anzsrc][payload] = 1
        anzsrc2subject[anzsrc]["total"] += 1
    else:
        anzsrc2subject[anzsrc][payload] += 1
        anzsrc2subject[anzsrc]["total"] += 1

def getBaseAnzsrc(subject):
    payload = subject["value"].lower().strip()
    if isDDC(subject):
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

        if anzsrcKey in anzsrcDict.keys():
            anzsrc = anzsrcDict[anzsrcKey]
        else:
            anzsrc = anzsrcDict["00"]
        return anzsrc
    elif isJEL(subject):
        anzsrc = anzsrcDict["14"]
        return anzsrc
    return ""

def getFullAnnotation(subjects, anzsrc2subject):
    ddc = []
    annotations = []
    seenAnzsrcMappings = []
    for subject in subjects:
        anzsrc = getBaseAnzsrc(subject)
        if not anzsrc:
            continue
        if not anzsrc in seenAnzsrcMappings:
            seenAnzsrcMappings.append(anzsrc)
            registerMapping(anzsrc, subject["value"], anzsrc2subject)
            annotations.append(anzsrc)
    return annotations

def getAnnotation(subjects, anzsrc2subject):
    annotations = []
    for annotation in getFullAnnotation(subjects, anzsrc2subject):
        annotations.append(annotation[:2].strip())
    return annotations

def getMinLength(field):
    if field == "description":
        return 15
    return 3

def getPayload(config, document):
    payload= {}
    for field in config["dmode"].split("_"):
        fieldPlural = field + "s"
        payloadPart = ""
        if fieldPlural not in document.keys():
            continue
        for instance in document[fieldPlural]:
            if len(instance["value"].split()) < getMinLength(field):
                continue
            try:
                if not detect(instance["value"]) == "en":
                    continue
            except LangDetectException as e:
                logger.warning("Cannot process {}: {}".format(instance["value"],e))
                continue
            payloadPart += " " + instance["value"]
        if not payloadPart:
            continue
        payload[field] = payloadPart
    return payload

def isSpecialChunk(fileName):
    specialRegex = re.compile(config["sregex"])
    if specialRegex.match(fileName):
        return True
    return False

def processChunk(fileName):
    logger.info("\tProcessing %s" % fileName)
    # todo: add labels for additional sources
    result = {
        "documents" : 0,
        "notAnnotatable": 0,
        "multiAnnotations": 0,
        "payloadNotFit": 0,
        "schemeURIs" : {},
        "subjectSchemes" : {},
        "anzsrc2subject" : {},
        "payload" : {},
    }
    with open(os.path.join(config["rawDataDir"], fileName)) as f:
        chunk = json.load(f)
        for document in chunk["documents"]:
            seenSchemeURIs = []
            seenSubjectSchemes = []
            result["documents"] += 1
            # todo: add quality-checks

            selectable = False
            if isSpecialChunk(fileName):
                selectable = True
            for subject in document["subjects"]:
                # count the documents with this schemeURI (once)
                if "schemeURI" in subject.keys():
                    schemeURI = subject["schemeURI"]
                    if schemeURI not in seenSchemeURIs:
                        seenSchemeURIs.append(schemeURI)
                        result["schemeURIs"][schemeURI] = (
                            result["schemeURIs"].get(schemeURI, 0) + 1)
                # count the doucments with this subjectScheme (once)
                if "subjectScheme" in subject.keys():
                    subjectScheme = subject["subjectScheme"]
                    if subjectScheme not in seenSchemeURIs:
                        seenSchemeURIs.append(subjectScheme)
                        result["subjectSchemes"][subjectScheme] = (
                            result["subjectSchemes"].get(subjectScheme, 0) + 1)
                if isAnnotatable(subject):
                    selectable = True

            if not selectable:
                result["notAnnotatable"] += 1
                continue

            if isSpecialChunk(fileName):
                annotation = specialDict[fileName]
            else:
                annotations = getAnnotation(document["subjects"],
                      result["anzsrc2subject"])
                if len(annotations) != 1:
                    result["multiAnnotations"] += 1
                    continue
                annotation = annotations[0]

            payload = getPayload(config, document)
            if not len(payload) == len(config["dmode"].split("_")):
                result["payloadNotFit"] += 1
                continue

            if not annotation in result["payload"].keys():
                result["payload"][annotation] = {}
            result["payload"][annotation][document["identifier"]["value"]] = (
                payload
            )
    logger.info("\tFinished processing {}".format(fileName))
    return result

################################################################################
# DIVIDE
################################################################################
worker = 4
logger.info("Starting %i workers" % worker)
dataRegex = re.compile(config["dregex"])
files = [f for f in os.listdir(config["rawDataDir"]) if dataRegex.match(f)]
#files = files[:1]
with ProcessPoolExecutor(
        max_workers = worker,
        initializer = init_factory
    ) as ex:
    res = zip(files, ex.map(processChunk, files))

################################################################################
# CONQUER
################################################################################
# TODO document, despaghettify
logger.info("Combining worker output")
documents = 0
notAnnotatable = 0
multiAnnotations = 0
payloadNotFit = 0
result = {}
anzsrc2subject = {}
subjectScheme = {}
schemeURI = {}
numAnnotations = {}
typeAnnotation = {}
for r in res:
    logger.info("processing results of {}".format(r[0]))
    documents += r[1]["documents"]
    notAnnotatable += r[1]["notAnnotatable"]
    multiAnnotations += r[1]["multiAnnotations"]
    payloadNotFit += r[1]["payloadNotFit"]
    for key in r[1]["payload"].keys():
        if not key in result.keys():
            result[key] = {}
        for identifier in r[1]["payload"][key]:
            result[key][identifier] = r[1]["payload"][key][identifier]
    for anzsrc in anzsrcDict.values():
        if anzsrc not in anzsrc2subject.keys():
            anzsrc2subject[anzsrc] = {"total": 0}
        if anzsrc in r[1]["anzsrc2subject"].keys():
            for key, value in r[1]["anzsrc2subject"][anzsrc].items():
                anzsrc2subject[anzsrc][key] = anzsrc2subject[anzsrc].get(key, 0) + value
    for key, value in r[1]["subjectSchemes"].items():
        subjectScheme[key] = subjectScheme.get(key, 0) + value
    for key, value in r[1]["schemeURIs"].items():
        schemeURI[key] = schemeURI.get(key, 0) + value

for key in result.keys():
    with open(os.path.join(config["dmaxDir"], key + ".data.json"), 'w') as crf:
        json.dump(result[key], crf)

with open("anzsrc2subject.json", "w") as mf:
    json.dump(anzsrc2subject, mf)

with open("subjectScheme.json", "w") as sf:
    json.dump(subjectScheme, sf)

with open("schemeURI.json", "w") as sf:
    json.dump(schemeURI, sf)

logger.info("Discipline match after data cleanup")
dataSize = 0
longestCategoryName = max(len(v) for k,v in anzsrcDict.items())
for category in sorted(result.keys()):
    categorySize = len(result[category])
    dataSize += categorySize
    logger.info("\t{:<{longestCategoryName}}: {:>12}".format(
        anzsrcDict[category],
        categorySize,
        longestCategoryName=longestCategoryName))
logger.info("General Statistics:")

logger.info("\tNumber of non-annotatable docs:    {:>12}".format(notAnnotatable))
logger.info("\tNumber of multi-annotated docs:    {:>12}".format(multiAnnotations))
logger.info("\tNumber of docs with unfit payload: {:>12}".format(payloadNotFit))
logger.info("\tNumber of useable documents:       {:>12}".format(dataSize))
logger.info("\tNumber of documents:               {:>12}".format(documents))
