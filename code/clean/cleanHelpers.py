import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import ijson
import json
import re
import util.util as util
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from cleanSchemeHelpers import getLabelFromScheme, getSchemeTester
from nltk.tokenize import word_tokenize

def cleanText(config, text):
    """
        Applies cleaning logic to a textual payload (stemmer, whitespace)

        Arguments
            config: dictionary with the configuration
            text: Payload to be cleaned (string)

        Returns cleaned payload
    """
    return re.sub("\s+", " ", text).strip().lower()

def getLabel(config, subject, row):
    """
        Returns a label to a given subject and updates the result row

        Arguments
            config: dictionary with the configuration
            subject: text payload as between the subject-tags in DataCite
            row: Current row of the resulting cleaned data table

        Returns label (id as defined in cleanDataHelpers)
    """
    for scheme in config["clean"]["schemes"]:
        isScheme = getSchemeTester(scheme)
        if isScheme and isScheme(config, subject):
            return getLabelFromScheme(scheme, config, subject, row)
    return None

def getPayload(config, document):
    """
        Returns the payload if it has the right language and is long enough

        Arguments
            config: dictionary with the configuration
            document: dictionary encoding DataCite-compliant metadata

        Returns dictionary including only valid text payloads
        (keys are as configured in config["clean"]["payload"])
    """
    payload= {}
    for field in config["clean"]["payloadFields"]:
        payloadPart = ""
        if field not in document.keys():
            continue
        #  each field (e.g. titles) might have several instances (title)
        for instance in document[field]:
            if not instance["value"]:
                continue
            try:
                if not detect(instance["value"]) == config["clean"]["lang"]:
                    continue
            except LangDetectException as e:
                continue
            payloadPart += " " + instance["value"]
        if len(payloadPart.split()) < config["clean"]["minLength"].get(field, 1):
            continue
        payload[field] = payloadPart
    return payload

def isSpecialChunk(config, fileName):
    """
        Indicates whether the file is configured as "special", meaning that
        it has not been retrieved from DataCite, but from a different source

        Arguments
            config: dictionary with the configuration
            fileName: string

        Returns boolean
    """
    if config["regex"]["special"].match(os.path.basename(fileName)):
        return True
    return False

def initResultRow(config):
    """
        Initializes a result row with default values

        Arguments
            config: dictionary with the configuration

        Returns dictionary with default values for a row in the result table
    """
    row = {
        "notAnnot": False,
        "multiAnnot": False,
        "notFit": False,
        "duplicate": False,
        "special": False,
        "useable": False,
        "schemeURI": set(),
        "subjectScheme": set(),
        "payload": {},
        "payloadHash": None,
        "labels": 0
    }
    for scheme in config["clean"]["schemes"]:
        row[scheme] = []
    return row

def finalizeRow(config, row):
    """
        Transforms the row of the result table into something serializable and

        Arguments
            config: dictionary with the configuration
            row: dictionary with the values to be serialized

        Returns dictionary with finalized values
    """
    for field in ("schemeURI", "subjectScheme"):
        row[field] = list(row[field])
    for scheme in config["clean"]["schemes"]:
        row[scheme] = "|".join(row[scheme])
    return row

def processFile(instruction):
    """
        Processes a file of metadata and saves the result in a json file

        Arguments:
            instruction: iterable, config dictionary first, filePath second

        Returns boolean indicating success or failure
    """
    (config, filePath) = instruction
    fileName = os.path.basename(filePath)
    fileId = config["regex"]["dataInput"].match(fileName).group(1)
    resultFile = os.path.join(config["clean"]["outputDir"], fileId + ".chunk.json")
    if os.path.isfile(resultFile):
        config["logger"].info("\t{} already processed: {}".format(
            os.path.basename(fileName),
            resultFile
        ))
        return True
    config["logger"].info("\tProcessing: {}".format(fileName))
    try:
        with open(filePath) as f:
            result = []
            docCounter = 0
            for document in ijson.items(f, 'documents.item'):
                row = initResultRow(config)
                if isSpecialChunk(config, fileName):
                    row["id"] = fileName + "_" + str(docCounter)
                    row["labels"] |= 1 << config["clean"]["special"][fileName]
                    row["special"] = True
                    docCounter += 1
                else:
                    row["id"] = document["identifier"]["value"]
                    for subject in document["subjects"]:
                        if "schemeURI" in subject.keys():
                            row["schemeURI"].add(subject["schemeURI"])
                        if "subjectScheme" in subject.keys():
                            row["subjectScheme"].add(subject["subjectScheme"])
                        label = getLabel(config, subject, row)
                        if label:
                            row["labels"] |= 1 << label
                if not row["labels"]:
                    row["notAnnot"] = True
                    result.append(finalizeRow(config, row))
                    continue
                elif not util.power_of_two(row["labels"]):
                    row["multiAnnot"] = True

                payloadDict = getPayload(config, document)
                # getPayload drops uncompliant fields -> payload is not fit!
                if not len(payloadDict.keys()) == len(config["clean"]["payloadFields"]):
                    row["notFit"] = True
                    result.append(finalizeRow(config, row))
                    continue
                row["useable"] = True
                row["payloadHash"] = util.getDictHash(payloadDict)
                row["payload"] = cleanText(config, " ".join(payloadDict.values()))
                result.append(finalizeRow(config, row))

        with open(resultFile, "w") as f:
            json.dump(result, f)
        config["logger"].info(
            "\tSave results for: {} ({} documents)".format(
                fileId,
                len(result)
            )
        )
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
