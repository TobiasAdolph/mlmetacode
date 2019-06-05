import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import re
import cleanDataHelpers

def getSchemeTester(scheme):
    if scheme == "anzsrc":
        return isAnzsrc
    elif scheme == "ddc":
        return isDdc
    elif scheme == "bk":
        return isBk
    elif scheme == "narcis":
        return isNarcis
    elif scheme == "linsearch":
        return isLinsearch
    elif scheme == "bepress":
        return isBepress
    else:
        return None

def getLabelFromScheme(scheme, config, subject, row):
    if scheme == "narcis":
        return getLabelFromMapping(scheme, "valueURI", subject, row)
    else:
        return getLabelFromMapping(scheme, "value", subject, row)

def isAnzsrc(config, subject):
    if not re.match(r'^\d{5}.*', subject["value"]):
        return False
    if "schemeURI" not in subject.keys():
        return False
    if (subject["schemeURI"] == "http://www.abs.gov.au/ausstats"
            "/abs@.nsf/0/6BB427AB9696C225CA2574180004463E"):
        return True
    return False

def isDdc(config, subject):
    if config["regex"]["ddcValue"].match(subject["value"].strip()):
        return False
    if subject.get("subjectScheme", "") in cleanDataHelpers.ddcNames:
        return True
    if config["regex"]["ddcSchemeURI"].match(subject.get("schemeURI", "")):
        return True
    return False

def isNarcis(config, subject):
    if subject.get("schemeURI", "") == "http://www.narcis.nl/classification":
        return True
    if subject.get("subjectScheme", "") == "NARCIS-classification":
        return True
    return False

def isLinsearch(config, subject):
    if subject.get("subjectScheme", "") == "linsearch":
        return True
    return False

def isBk(config, subject):
    if subject.get("subjectScheme", "") == "bk":
        return True
    return False

def isBepress(config, subject):
    subjectScheme = subject.get("subjectScheme", "").strip().lower()
    for bsn in (
        "bepress digital commons three-tiered taxonomy",
        "digital commons three-tiered list of academic disciplines"):
        if subjectScheme == bsn:
            return True
    return False

def getLabelFromMapping(scheme, field, subject, row):
    checkAgainst = subject.get(field, "").strip()
    if not checkAgainst:
        return None
    mapping = cleanDataHelpers.mappings[scheme]
    for pair in mapping:
        label = pair[0]
        regex  = pair[1]
        if regex.match(checkAgainst):
            row[scheme].append(subject.get(field, ""))
            return label
    return None
