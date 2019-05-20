import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import glob
import ijson
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

DDCValueRegex = re.compile('(^\d+\.\d+,)+')
JELSubjecSchemeRegex = re.compile('^JEL.*')

chunksDir = os.path.join(config["processedDataDir"], "clean", "chunks")

if not os.path.isdir(chunksDir):
    os.mkdir(chunksDir)

########################################
# LOGGING
########################################
logger = logging.getLogger('clean')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(os.path.join(config["logDir"], 'clean.log'))
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s|%(process)d -- %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)
logger.info("Starting clean with config {}".format(config["hash"]))

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
    if DDCValueRegex.match(subject["value"].strip()):
        return False
    if subject["subjectScheme"] in ddcNames:
        return True
    return False

def isJEL(subject):
    if "subjectScheme" not in subject.keys():
        return False
    if JELSubjecSchemeRegex.match(subject["subjectScheme"]):
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
                logger.debug("Cannot process {}: {}".format(instance["value"],e))
                continue
            payloadPart += " " + instance["value"]
        if len(payloadPart.split()) < getMinLength(field):
            continue
        payload[field] = payloadPart
    return payload

def isSpecialChunk(fileName):
    specialRegex = re.compile(config["sregex"])
    if specialRegex.match(fileName):
        return True
    return False

def processFile(fileName):
    resultFile = os.path.join(config["processedDataDir"], "clean", "chunks", fileName)
    if os.path.isfile(resultFile):
        logger.info("\t{}: already processed".format(fileName))
        return True
    logger.info("\t{}: Start processing".format(fileName))
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
        for document in ijson.items(f, 'documents.item'):
            seenSchemeURIs = []
            seenSubjectSchemes = []
            labels = set()
            result["documents"] += 1

            if isSpecialChunk(fileName):
                labels.add(specialDict[fileName])

            if "subjects" not in document.keys():
                # special chunks may have no subject (fixed label)
                if isSpecialChunk(filenName):
                    result["notAnnotatable"] += 1
                    continue
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
                    anzsrc = getBaseAnzsrc(subject)
                    if not anzsrc:
                        continue

                    registerMapping(anzsrc,
                                    subject["value"],
                                    result["anzsrc2subject"])
                    labels.add(anzsrc[:2].strip())

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

            if not label in result["payload"].keys():
                result["payload"][label] = {}

            payloadHash = util.getDictHash(payload)
            result["payload"][label][payloadHash] = payload
    with open(resultFile, "w") as f:
        json.dump(result, f)
    return True

################################################################################
# DIVIDE
################################################################################
worker = 4
logger.info("Starting %i workers" % worker)
dataRegex = re.compile(config["dregex"])


files = [f for f in glob.glob(config["rawDataDir"] + "/*") if dataRegex.match(f)]

files.sort(key=lambda x: os.path.getsize(x), reverse=True)
files = [os.path.basename(f) for f in files]

with ProcessPoolExecutor(
        max_workers = worker,
        initializer = init_factory
    ) as ex:
    res = zip(files, ex.map(processFile, files))

################################################################################
# CONQUER
################################################################################
# TODO document
logger.info("Combining worker output")
results = {
    "useableDocuments": 0,
    "documents" : 0,
    "notAnnotatable": 0,
    "multiAnnotations": 0,
    "payloadNotFit": 0,
    "schemeURIs" : {},
    "subjectSchemes" : {},
    "anzsrc2subject" : {},
    "payload" : {},
}

files = [f for f in glob.glob(chunksDir + "/*") if dataRegex.match(f)]

for anzsrc in anzsrcDict.values():
    results["anzsrc2subject"][anzsrc] = {"total": 0}

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

        if anzsrc in result["anzsrc2subject"].keys():
            for key, value in result["anzsrc2subject"][anzsrc].items():
                results["anzsrc2subject"][anzsrc][key] = (
                    anzsrc2subject[anzsrc].get(key, 0) + value )

    for key, value in result["subjectSchemes"].items():
        results["subjectSchemes"][key] = results["subjectSchemes"].get(key, 0) + value

    for key, value in result["schemeURIs"].items():
        results["schemeURIs"][key] = results["schemeURIs"].get(key, 0) + value

for key in results["payload"].keys():
    with open(os.path.join(config["processedDataDir"], "clean", key + ".data.json"), 'w') as f:
        json.dump(results["payload"][key], f)

for key in results.keys():
    if key in ("anzsrc2subject", "subjectSchemes", "schemeURIs"):
        with open(os.path.join(config["processedDataDir"], "clean", key + ".json"), "w") as f:
            json.dump(results[key], f)

logger.info("Discipline match after data cleanup")

longestCategoryName = max(len(v) for k,v in anzsrcDict.items())
for category in sorted(results["payload"].keys()):
    categorySize = len(results["payload"][category])
    results["useableDocuments"] += categorySize
    logger.info("\t{:<{longestCategoryName}}: {:>12}".format(
        anzsrcDict[category],
        categorySize,
        longestCategoryName=longestCategoryName))

logger.info("General Statistics:")
logger.info("\tNumber of non-annotatable docs:    {:>12}".format(results["notAnnotatable"]))
logger.info("\tNumber of multi-annotated docs:    {:>12}".format(results["multiAnnotations"]))
logger.info("\tNumber of docs with unfit payload: {:>12}".format(results["payloadNotFit"]))
logger.info("\tNumber of useable documents:       {:>12}".format(results["useableDocuments"]))
logger.info("\tNumber of documents:               {:>12}".format(results["documents"]))
