import json
import logging
import os
import random
import re
import requests
import subprocess
import sys
import time

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

def doHarvest(payload):
    config = payload[0]
    fileName = payload[1]
    retrievalID = re.match(r'.*/(([0-9]|[a-f]){2}).config.json',
                           fileName).group(1)
    target = os.path.join(config["targetDir"], retrievalID + ".json")
    if os.path.isfile(target):
        logger.warn("{} already exists, skipping")
        return True
    logger.info("================> do harvest with {} ({})".format(retrievalID, fileName))
    hvIdx = getFreeHarvester()
    if hvIdx == -1:
        logger.error("Error, no hv is available")
        raise Exception("ERROR")
    try:
        hv = config["hvs"][hvIdx]
        logger.debug("using {}".format(hv))
        hvConfig = loadHvConfig(fileName)
        loadHarvester(hvConfig, hv, config)
        startHarvester(hv)
        hvState = "HARVESTING"
        while hvState in ["HARVESTING", "QUEUED"]:
            time.sleep(config["sleep"])
            logger.info("slept {} seconds, checking harvester".format(config["sleep"]))
            hvState = checkHarvester(hv)
        logger.info("Harvester finished with state {}".format(hvState))
        returnHarvester(hvIdx)
        if hvState == "IDLE":
            time.sleep(5)
            unloadHarvester(hvIdx, config, target)
            return True
        else:
            logger.error("Harvester finished with status code {}".format(hvState))
            return False

    except Exception as e:
        logger.error(e)
        returnHarvester(hvIdx)
        return False

def loadHarvester(hvConfig, hv, config):
    logger.info("Loading harvester {} with hvconfig {}".format(hv, hvConfig["OaiPmhETL.hostURL"]))
    headers = {'Content-Type': "application/json"}
    hvUrl = "{}/config/_set".format(hv)
    hvConfig["OaiPmhETL.rangeTo"] = config["hvRangeTo"]
    try:
        r = requests.post(hvUrl, data=json.dumps(hvConfig), headers=headers)
        logger.info("{} {}".format(r.status_code, r.reason))
    except Exception as e:
        logger.error(e)

def checkHarvester(hv):
    logger.info("Checking harvester {}".format(hv))
    hvUrl = hv
    r = requests.get(hvUrl)
    logger.debug("{} {} {}".format(r.status_code, r.reason, r.text))
    hvState = json.loads(r.text)["state"]
    logger.debug("Harvester state: {}".format(hvState))
    return hvState

def startHarvester(hv):
    hvUrl = hv
    r = requests.post(hvUrl)
    logger.debug("{} {} {}".format(r.status_code, r.reason, r.text))

def unloadHarvester(hvIdx, config, target):
    logger.debug("unload {}".format(hvIdx))
    subprocess.run(config["hvUnloadCmd"].format(config["hvUnloadSrc"][hvIdx],
                                             target).split())

def loadHvConfig(hvConfigPath):
    with open(hvConfigPath, "r") as f:
        return json.load(f)

def init_globals(hvs):
    global _HVS
    _HVS = hvs

def getFreeHarvester():
    logger.info("Calling getFreeHarvester")
    with _HVS.get_lock():
        freeIdx = -1
        for idx, isFree in enumerate(_HVS):
            logger.debug("{}: {}".format(idx, isFree))
            if isFree:
                logger.debug("Hv {} is free".format(idx))
                freeIdx = idx
                _HVS[idx] = False
                break
    if freeIdx == -1:
        logger.error("No hv free for a worker, raise hv in config")
    return freeIdx

def returnHarvester(hvIdx):
    logger.debug("Returning harvester {}".format(hvIdx))
    with _HVS.get_lock():
         _HVS[hvIdx] = True
