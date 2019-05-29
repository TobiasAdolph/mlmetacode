import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import re
from cleanDataHelpers import *

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
    else:
        return None

def getAnzsrcFromScheme(scheme, config, subject):
    if scheme == "anzsrc":
        return getAnzsrc(config, subject)
    elif scheme == "ddc":
        return getDdc(config, subject)
    elif scheme == "bk":
        return getBk(config, subject)
    elif scheme == "narcis":
        return getNarcis(config, subject)
    elif scheme == "linsearch":
        return getLinsearch(config, subject)
    else:
        return None

def isAnzsrc(config, subject):
    if "schemeURI" not in subject.keys():
        return False
    if (subject["schemeURI"] == "http://www.abs.gov.au/ausstats"
            "/abs@.nsf/0/6BB427AB9696C225CA2574180004463E"):
        return True
    return False

def isDdc(config, subject):
    if config["regex"]["ddcValue"].match(subject["value"].strip()):
        return False
    if subject.get("subjectScheme", "") in ddcNames:
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

def getAnzsrcSchemeFromMapping(mapping, field, subject):
    for pair in mapping:
        anzsrc = pair[0]
        regex  = pair[1]
        if regex.match(subject.get(field, "").lower().strip()):
            return anzsrc
    return None

def getAnzsrc(config, subject):
    payload = subject.get("value", "").lower().strip()
    if not re.match(r'^\d{5}.*', payload):
        return None
    anzsrcNumber = re.search('\d+', payload).group()
    if len(anzsrcNumber) % 2 == 0:
        return int(payload[:2])
    else:
        return int(payload[:1])

def getDdc(config, subject):
    return getAnzsrcSchemeFromMapping(ddc2Anzsrc, "value", subject)

def getNarcis(config, subject):
    return getAnzsrcSchemeFromMapping(narcis2Anzsrc, "valueURI", subject)

def getBk(config, subject):
    return getAnzsrcSchemeFromMapping(bk2Anzsrc, "value", subject)

def getLinsearch(config, subject):
    return getAnzsrcSchemeFromMapping(linsearch2Anzsrc, "value", subject)
