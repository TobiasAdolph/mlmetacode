import glob
import json
import pprint
import sys
import re
import os
from concurrent.futures import ProcessPoolExecutor

################################################################################
# CONFIGURATION
################################################################################
base_dir="/home/di72jiv/Documents/src/gerdi/ml/2019-03-02/"
dataRegex = re.compile('[0-9a-f]{2}\.json$')
# used to check the subject[subjectScheme] payload to determine whether this is
# a dewey decimal subject
ddcNames = [
        "Dewey decimal Classification",
        "Dewey-Dezimalklassifikation (DDC) (http://ddc-deutsch.de/)",
        "DeweyDecimalClassification",
        "dewey",
        "ddccode",
        "ddc",
        "Dewey Classification"
            " (http://opac.bncf.firenze.sbn.it/opac/controller.jsp"
            "?action=dewey_browse&deweypath_cod=9)",
        "DDC (Dewey-Dezimalklassifikation) (http://www.ddc-deutsch.de)",
        "DDC"]

# Used to map the payload (subject["value"]) of a DDC-subject to the base classes
# of ANZSRC. Unhandled DDC classes:
#  ^03[^.] | Encyclopedias & books of facts
#  ^04[^.] | Unassigned (formerly Biographies)
#  ^05[^.] | Magazines, journals & serials
#  ^06[^.] | Associations, organizations & museums
#  ^08[^.] | Quotations
#  ^09[^.] | Manuscripts & rare books
#  ^35[^.] | Public administration & military science
#  ^39[^.] | Customs, etiquette, & folklore
#  ^50[^.] | Science (too specific, subcategories are partly handled)
#  ^64[^.] | Home & family management
#  ^79[^.] | Sports, games & entertainment
#  ^91[^.] | Geography & travel
#  ^92[^.] | Biography & genealogy

# ! order matters: first come first serve, rearranging might result in false
# positives

mappingDDC = [
        ["04 earth sciences",
            re.compile(
                '^55[^.]+.*'
                '|^56[^.]+.*'
                '|^ddc 55[^.]+.*'
                '|^ddc 56[^.]+.*'
                '|.*earth sciences and geology$'
                '|.*550\s*\|\s*geowissenschaften.*'
                '|^912$'
                '|geowissenschaften$'
            )
        ],
        ["11 medical and health sciences",
            re.compile(
                '^61[^.]+.*'
                '|^ddc 61[^.]+.*'
                '|^medizin und gesundheit'
                )
        ],
        ["06 biological sciences",
            re.compile(
                '^57[^.]+.*'
                '|^58[^.]+.*'
                '|^59[^.]+.*'
                '|^ddc 57[^.]+.*'
                '|^ddc 58[^.]+.*'
                '|^ddc 59[^.]+.*'
                '|.*naturwissenschaften::570.*'
                '|.*naturwissenschaften::580.*'
                '|.*naturwissenschaften::590.*'
                '|biology'
                )
        ],
        ["08 information and computing sciences",
            re.compile(
                '^00[^.]+.*'
                '|^01[^.]+.*'
                '|^02[^.]+.*'
                '|^ddc 00[^.]+.*'
                '|^ddc 01[^.]+.*'
                '|^ddc 02[^.]+.*'
                '|.*allgemeines, wissenschaft::000.*$'
                '|^bibliotheks- und informationswissenschaften$'
                )
        ],
        ["14 economics",
            re.compile(
                '^33[^.]+.*'
                '|^ddc 33[^.]+.*'
                '|^wirtschaft$'
                )
        ],
        ["09 engineering",
            re.compile(
                '^62[^.]+.*'
                '|^ddc 62[^.]+.*'
                '|.*technik::620.*'
                )
        ],
        ["02 physical science",
            re.compile(
                '^52[^.]+.*'
                '|^53[^.]+.*'
                '|^ddc 52[^.]+.*'
                '|^ddc 53[^.]+.*'
                '|.*530 \| physik.*'
                )
        ],
        ["21 history and archaeology",
                re.compile(
                    '^90[^.]+.*'
                    '|^93[^.]+.*'
                    '|^94[^.]+.*'
                    '|^95[^.]+.*'
                    '|^96[^.]+.*'
                    '|^97[^.]+.*'
                    '|^98[^.]+.*'
                    '|^99[^.]+.*'
                    '|^ddc 90[^.]+.*'
                    '|^ddc 93[^.]+.*'
                    '|^ddc 94[^.]+.*'
                    '|^ddc 95[^.]+.*'
                    '|^ddc 96[^.]+.*'
                    '|^ddc 97[^.]+.*'
                    '|^ddc 98[^.]+.*'
                    '|^ddc 99[^.]+.*'
                    '|^271.*'
                    )
        ],
        ["03 chemical science",
                re.compile(
                    '^54[^.]+.*'
                    '|^54[^.]+.*'
                    '|.*540 \| chemie.*'
                    )
        ],
        ["20 language, communication and culture",
                re.compile(
                    '^4\d+[^.]+.*'
                    '|^8\d+[^.-]+.*'
                    '|^306.*'
                    '|^ddc 4[^.]+.*'
                    '|^ddc 8[^.]+.*'
                    '|^ddc 306.*'
                    '|^8 language\. linguistics\. literature$'
                    '|^81 linguistics and languages'
                    '|.*dewey decimal classification::400 \| sprache, linguistik.*$'
                    '|.*dewey decimal classification::800 \| literatur, rhetorik, literaturwissenschaft.*$'
                    )
        ],
        ["16 studies in human society",
                re.compile(
                    '^30[^.]+.*'
                    '|^32[^.]+.*'
                    '|^36[^.]+.*'
                    '|^ddc 30[^.]+.*'
                    '|^ddc 32[^.]+.*'
                    '|^ddc 36[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::330$'
                    '|.*sozialwissenschaften, soziologie, anthropologie::330.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::360.*'
                    '|^soziale probleme und sozialdienste; verbände$'
                    '|^0 social sciences'
                    '|^3 social sciences$'
                    '|^sozialwissenschaften$'
                    )
        ],
        ["07 agricultural and veterinary science",
                re.compile(
                    '^63[^.]+.*'
                    '|^ddc 63[^.]+.*'
                    '|^landwirtschaft und verwandte bereiche$'
                    '|.*technik::630.*'
                    )
        ],
        ["17 psychology and cognitive sciences",
                re.compile(
                    '^15[^.]+.*'
                    '|^ddc 15[^.]+.*'
                    '|^psychologie$'
                    )
        ],
        ["10 technology",
                re.compile(
                    '^60[^.]+.*'
                    '|^ddc 60[^.]+.*'
                    )
        ],
        ["13 education",
                re.compile(
                    '^37[^.]+.*'
                    '^507.*'
                    '|^ddc 37[^.]+.*'
                    '|^ddc 507.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::370.*'
                    )
        ],
        ["01 mathematical science",
                re.compile(
                    '^31\d+.*'
                    '|^51[^.]+.*'
                    '|^ddc 31[^.]+.*'
                    '|^ddc 51[^.]+.*'
                    '|.*510 \| mathematik.*'
                    )
        ],
        ["18 law and legal studies",
                re.compile(
                    '^34[^.]+.*'
                    '|^ddc 34[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::340.*'
                    '|^recht$'
                    )
        ],
        ["22 philosophy and religious studies",
                re.compile(
                    '^(1|2)\d+.*'
                    '|^507.*'
                    '|^ddc (1|2)[^.]+.*'
                    '|^ddc 507.*'

                    )
        ],
        ["09 engineering",
                re.compile(
                    '^62[^.]+.*'
                    '|^66[^.]+.*'
                    '|^67[^.]+.*'
                    '|^68[^.]+.*'
                    '|^ddc 62[^.]+.*'
                    '|^ddc 66[^.]+.*'
                    '|^ddc 67[^.]+.*'
                    '|^ddc 68[^.]+.*'
                    )
        ],
        ["10 technology",
                re.compile(
                    '^60[^.]+.*'
                    '|^ddc 60[^.]+.*'
                    '|.*600 \| technik.*$')
        ],
        ["19 studies in creative arts and writing",
                re.compile(
                    '^07[^.]+.*'
                    '|^70[^.]+.*'
                    '|^73[^.]+.*'
                    '|^74[^.]+.*'
                    '|^75[^.]+.*'
                    '|^76[^.]+.*'
                    '|^77[^.]+.*'
                    '|^78[^.]+.*'
                    '|^ddc 07[^.]+.*'
                    '|^ddc 70[^.]+.*'
                    '|^ddc 73[^.]+.*'
                    '|^ddc 74[^.]+.*'
                    '|^ddc 75[^.]+.*'
                    '|^ddc 76[^.]+.*'
                    '|^ddc 77[^.]+.*'
                    '|^ddc 78[^.]+.*'
                    )
        ],
        ["15 commerce, management, tourism and services",
                re.compile(
                    '^38[^.]+.*'
                    '|^65[^.].*'
                    '|^ddc 38[^.]+.*'
                    '|^ddc 65[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::380.*'
                    )
        ],
        ["12 built environment and design",
                re.compile(
                    '^69[^.*]'
                    '|^71[^.*]'
                    '|^72[^.*]'
                    '|^ddc 69[^.]+.*'
                    '|^ddc 71[^.]+.*'
                    '|^ddc 72[^.]+.*'
                    )
        ]
]
# Used to map the payload (subject["value"]) of a ANZSRC-subject to the base
# classes of ANZSRC
anzsrcBaseClasses = {
        "00" : "00 uncategorized",
        "01" : "01 mathematical science",
        "02" : "02 physical science",
        "03" : "03 chemical science",
        "04" : "04 earth sciences",
        "05" : "05 environmental sciences",
        "06" : "06 biological sciences",
        "07" : "07 agricultural and veterinary science",
        "08" : "08 information and computing sciences",
        "09" : "09 engineering",
        "10" : "10 technology",
        "11" : "11 medical and health sciences",
        "12" : "12 built environment and design",
        "13" : "13 education",
        "14" : "14 economics",
        "15" : "15 commerce, management, tourism and services",
        "16" : "16 studies in human society",
        "17" : "17 psychology and cognitive sciences",
        "18" : "18 law and legal studies",
        "19" : "19 studies in creative arts and writing",
        "20" : "20 language, communication and culture",
        "21" : "21 history and archaeology",
        "22" : "22 philosophy and religious studies"
}

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

def isAscii(s):
    return all(ord(c) < 128 for c in s)

def isEnglish(field):
    if field.get("lang", "?") == "en":
        return True
    if isAscii(field["value"]):
        return True
    return False

def getEnglishValueOrEmpty(field, document):
    if field in document.keys():
        for instance in document[field]:
            if isEnglish(instance):
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

        if anzsrcKey in anzsrcBaseClasses.keys():
            anzsrc = anzsrcBaseClasses[anzsrcKey]
        else:
            anzsrc = anzsrcBaseClasses["00"]
        return anzsrc
    elif isJEL(subject):
        anzsrc = anzsrcBaseClasses["14"]
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

def addTo(name, bucket, seen, addee):
    if name not in addee.keys() or addee[name] in seen:
        return
    bucket[addee[name]] = bucket.get(addee[name], 0) + 1

def processChunk(fileName):
    print("\tProcessing %s" % fileName)
    documents = 0
    schemeURIs = {}
    subjectSchemes = {}
    anzsrc2subject = {}
    result = {}
    with open(base_dir + fileName) as f:
        chunk = json.load(f)
        for document in chunk["documents"]:
            alreadySeenSchemeURIs = []
            alreadySeenSubjectSchemes = []
            documents += 1
            selectable = False
            for subject in document["subjects"]:
                addTo("schemeURI",
                        schemeURIs,
                        alreadySeenSchemeURIs,
                        subject)
                addTo("subjectScheme",
                        subjectSchemes,
                        alreadySeenSubjectSchemes,
                        subject)
                if isAnnotatable(subject):
                    selectable = True
            if selectable:
                annotations = getAnnotation(document["subjects"],
                      anzsrc2subject)
                if len(annotations) != 1:
                    continue
                annotation = annotations[0]

                title = getEnglishValueOrEmpty("titles", document)
                if not title:
                    continue

                description =  getEnglishValueOrEmpty("descriptions", document)
                if not description:
                    continue

                if not annotation in result.keys():
                    result[annotation] = {}
                result[annotation][document["identifier"]["value"]] = (
                    {
                        "title": title,
                        "description": description
                    }
                )
    return {
                "documents": documents,
                "schemeURI": schemeURIs,
                "subjectScheme": subjectSchemes,
                "anzsrc2subject": anzsrc2subject,
                "result": result
           }

################################################################################
# DIVIDE
################################################################################
worker = 4
print("Starting %i workers" % worker)
files = [f for f in os.listdir(base_dir) if dataRegex.match(f)]
#files = files[:1]
with ProcessPoolExecutor(worker) as ex:
    res = zip(files, ex.map(processChunk, files))

################################################################################
# CONQUER
################################################################################
print("Combining worker output")
documents = 0
result = {}
anzsrc2subject = {}
subjectScheme = {}
schemeURI = {}
numAnnotations = {}
typeAnnotation = {}
for r in res:
    documents += r[1]["documents"]
    for key in r[1]["result"].keys():
        if not key in result.keys():
            result[key] = {}
        for identifier in r[1]["result"][key]:
            result[key][identifier] = r[1]["result"][key][identifier]
    for anzsrc in anzsrcBaseClasses.values():
        if anzsrc not in anzsrc2subject.keys():
            anzsrc2subject[anzsrc] = {"total": 0}
        if anzsrc in r[1]["anzsrc2subject"].keys():
            for key, value in r[1]["anzsrc2subject"][anzsrc].items():
                anzsrc2subject[anzsrc][key] = anzsrc2subject[anzsrc].get(key, 0) + value
    for key, value in r[1]["subjectScheme"].items():
        subjectScheme[key] = subjectScheme.get(key, 0) + value
    for key, value in r[1]["schemeURI"].items():
        schemeURI[key] = schemeURI.get(key, 0) + value

for key in result.keys():
    with open(key + ".data.json", 'w') as crf:
        json.dump(result[key], crf)

with open("anzsrc2subject.json", "w") as mf:
    json.dump(anzsrc2subject, mf)

with open("subjectScheme.json", "w") as sf:
    json.dump(subjectScheme, sf)

with open("schemeURI.json", "w") as sf:
    json.dump(schemeURI, sf)


print("General Statistics:")
print("\tNumber of documents:  %i" %documents)
print("\tSize of cleaned recs: %i" % sum(len(discp) for discp in result))
print("Discipline match before data cleanup")
for key in sorted(anzsrc2subject.keys()):
    print("\t%s: %s" % (key, anzsrc2subject[key].get("total", 0)))
print("Discipline match after data cleanup")
for key in sorted(result.keys()):
    print("\t%s: %s" % (anzsrcBaseClasses[key], len(result[key])))
