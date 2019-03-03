import glob
import json
import pprint
import sys
import re

################################################################################
# CONFIGURATION
################################################################################
base_dir="/home/di72jiv/Documents/phd/code/zenodo/data/"

# used to check the subject[subjectScheme] payload to determine whether this is
# a dewey decimal subject
ddcNames = [
        "udc",
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
#  ^50[^.] | Science (too specific, subcategories are partly handled)
#  ^64[^.] | Home & family management
#  ^79[^.] | Sports, games & entertainment

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
                '|^ddc 57[^.]+.*'
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
                '|.*330.*wirtschaft.*$'
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
                    '|^92[^.]+.*'
                    '|^93[^.]+.*'
                    '|^94[^.]+.*'
                    '|^95[^.]+.*'
                    '|^96[^.]+.*'
                    '|^97[^.]+.*'
                    '|^98[^.]+.*'
                    '|^99[^.]+.*'
                    '|^911.*'
                    '|^271.*'
                    '|^ddc 90[^.]+.*'
                    '|^ddc 92[^.]+.*'
                    '|^ddc 93[^.]+.*'
                    '|^ddc 94[^.]+.*'
                    '|^ddc 95[^.]+.*'
                    '|^ddc 96[^.]+.*'
                    '|^ddc 97[^.]+.*'
                    '|^ddc 98[^.]+.*'
                    '|^ddc 99[^.]+.*'
                    '|^ddc 911.*'
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
                    '|^39[^.]+.*'
                    '|^306.*'
                    '|^ddc 4[^.]+.*'
                    '|^ddc 8[^.]+.*'
                    '|^ddc 39[^.]+.*'
                    '|^ddc 306.*'
                    '|^8 language\. linguistics\. literature$'
                    '|^81 linguistics and languages'
                    '|.*dewey decimal classification::400 | sprache, linguistik.*$'
                    '|.*literatur, rhetorik, literaturwissenschaft.*'
                    )
        ],
        ["16 studies in human society",
                re.compile(
                    '^30[^.]+.*'
                    '|^32[^.]+.*'
                    '|^35[^.]+.*'
                    '|^36[^.]+.*'
                    '|^91[0,2,3,4,5,6,7,8,9]+.*'
                    '|^ddc 30[^.]+.*'
                    '|^ddc 32[^.]+.*'
                    '|^ddc 35[^.]+.*'
                    '|^ddc 36[^.]+.*'
                    '|^ddc 91[0,2,3,4,5,6,7,8,9]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie$'
                    '|.*sozialwissenschaften, soziologie, anthropologie::320.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::330.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::360.*'
                    '|.*geschichte und geografie::910.*'
                    '|^soziale probleme und sozialdienste; verbände$'
                    '|^0 social sciences'
                    '|^3 social sciences$'
                    '|^sozialwissenschaften$'
                    '|^öffentliche verwaltung, militärwissenschaft$'
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
                    '|^bildung und erziehung$'
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
        "1" : "01 mathematical science",
        "2" : "02 physical science",
        "3" : "03 chemical science",
        "4" : "04 earth sciences",
        "5" : "05 environmental sciences",
        "6" : "06 biological sciences",
        "7" : "07 agricultural and veterinary science",
        "8" : "08 information and computing sciences",
        "9" : "09 engineering",
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

# Initialize values (no need to change)
documents = 0
mapped = {}
result = []
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
    if "schemeURI" not in subject.keys():
        return False
    if subject["schemeURI"] == "JEL":
        return True
    else:
        return False

def isAnnotatable(subject):
    if isDDC(subject) or isJEL(subject) or isANZSRC(subject):
        return True
    else:
        return False

def getFieldOrEmpty(field, document):
    if field == "subjects":
        subjects = []
        for subject in document["subjects"]: 
            if isAnnotatable(subject): 
                continue
            subjects.append(subject)
        return subjects
    if field in document.keys():
        return document[field]
    else:
        return getEmptyField(field) 

def getEmptyField(field):
    if field == "publisher":
        return ""
    elif field in ["subjects", "descriptions", "titles"]:
        return []
    elif field == "resourceType":
        return {"resourceType": { "value": "", "resourceTypeGeneral": ""}}
        

def registerMapping(anzsrc, payload):
    if anzsrc not in mapped.keys():
        mapped[anzsrc] = { payload: 1, "total": 1}
    elif payload not in mapped[anzsrc].keys():
        mapped[anzsrc][payload] = 1
        mapped[anzsrc]["total"] += 1
    else: 
        mapped[anzsrc][payload] += 1
        mapped[anzsrc]["total"] += 1

def getBaseAnzsrc(payload, type="ddc"):
    if type == "ddc":
        for pair in mappingDDC:
            anzsrc = pair[0]
            regex  = pair[1]
            if regex.match(payload):
                registerMapping(anzsrc, payload)
                return anzsrc
        registerMapping("0", payload)
        return ""
    elif type == "anzsrc":
        anzsrcNumber = re.search('\d+', payload).group()
        if len(anzsrcNumber) % 2 == 0:
            anzsrc = anzsrcBaseClasses[payload[:2]]
        else: 
            anzsrc = anzsrcBaseClasses[payload[:1]]
        registerMapping(anzsrc, payload)
        return anzsrc
    elif type == "jel":
        anzsrc = anzsrcBaseClasses["14"]
        registerMapping(anzsrc, payload)
        return anzsrc

def getFullAnnotation(subjects):
    ddc = []
    annotations = []
    for subject in document["subjects"]:
        if isDDC(subject):
            anzsrc = getBaseAnzsrc((subject["value"].lower().strip()))
            if anzsrc:
                annotations.append(anzsrc)
        elif isANZSRC(subject):
            annotations.append(getBaseAnzsrc(subject["value"].lower().strip(),
                "anzsrc"))
        elif isJEL(subject):
            annotations.append(getBaseAnzsrc(subject["value"].lower().strip(),
                "jel"))
    return annotations

def getAnnotation(subjects):
    annotations = []
    for annotation in getFullAnnotation(subjects):
        annotations.append(annotation[:2].strip())
    return annotations

################################################################################
# MAIN LOOP
################################################################################
for cur_file in glob.glob(base_dir + "*_*.json"):
#    print(cur_file)
    if (cur_file == "/home/di72jiv/Documents/phd/code/zenodo/data/2017_05.json" or 
        cur_file == "/home/di72jiv/Documents/phd/code/zenodo/data/2017_06.json"):
        continue
    with open(cur_file) as f:
        chunk = json.load(f)
        documents += len(chunk["documents"])
        for document in chunk["documents"]:
            selectable = False
            for subject in document["subjects"]:
                if isAnnotatable(subject):
                    selectable = True
            if selectable:
                add = {
                        "payload": {},
                        "annotation": {}
                }
                add["payload"]["publisher"] = (
                    getFieldOrEmpty("publisher", document))
                add["payload"]["resourceType"] = (
                    getFieldOrEmpty("resourceType", document))
                add["payload"]["subjects"] = (
                    getFieldOrEmpty("subjects", document))
                add["payload"]["titles"] = (
                    getFieldOrEmpty("titles", document))
                add["payload"]["descriptions"] = (
                    getFieldOrEmpty("descriptions", document))
                add["annotation"] = (
                    getAnnotation(document["subjects"]))
                if len(add["annotation"]) < 1:
                    continue
                result.append(add)

################################################################################
# POSTPROCESSING
################################################################################
with open("data.json", 'w') as crf:
    json.dump(result, crf)

pprint.pprint(mapped)
for key, value in mapped.items():
    print("%s: %s" % (value["total"], key))
print("Number of documents:  %i" %documents)
print("Size of cleaned recs: %i" % len(result))
