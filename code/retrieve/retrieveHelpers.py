import json
import logging
import os
import random
import re
import requests
import subprocess
import sys
import time

logger = logging.getLogger('retrieve')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('retrieve.log')
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s|%(asctime)s -- %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

def doHarvest(payload):
    config = payload[0]
    fileName = payload[1]
    retrievalID = re.match(r'.*/(([0-9]|[a-f]){2}).config.json',
                           fileName).group(1)
    target = os.path.join(config["targetDir"], retrievalID + ".json")
    if os.path.isfile(target):
        logger.warn("{} already exists, skipping".format(retrievalID))
        return True
    logger.info("================> do harvest with {} ({})".format(retrievalID, fileName))
    hvIdx = getFreeHarvester()
    if hvIdx == -1:
        logger.error("Error, no hv is available")
        raise Exception("ERROR")
    try:
        hv = config["hvs"][hvIdx]
        hvConfig = loadHvConfig(fileName)
        logger.info("using {} for {} with url and unload to {}".format(
            hv,
            fileName,
            config["hvUnloadSrc"][hvIdx]))

        logger.info("Loading harvester {} for {} with hvconfig {}".format(
            hv,
            fileName,
            hvConfig["OaiPmhETL.hostURL"]))
        loadHarvester(hvConfig, hv, config)
        startHarvester(hv)
        hvState = "HARVESTING"
        while hvState in ["HARVESTING", "QUEUED"]:
            time.sleep(config["sleep"])
            logger.debug("Harvester {} for {} slept {} seconds, checking harvester".format(
                hv,
                fileName,
                config["sleep"]))
            (hvState, hvHealth) = checkHarvester(hv)
        logger.info("Harvester {} for {} finished with state {} and health {}".format(
            hv,
            fileName,
            hvState,
            hvHealth)
        )
        returnHarvester(hvIdx)
        if hvState == "IDLE":
            time.sleep(5)
            unloadHarvester(hvIdx, config, target)
            return True
        else:
            logger.error("Harvester {} for {} finished with status code {}".format(
                hv,
                fileName,
                hvState)
            )
            return False

    except Exception as e:
        logger.error(e)
        returnHarvester(hvIdx)
        return False

def loadHarvester(hvConfig, hv, config):
    headers = {'Content-Type': "application/json"}
    hvUrl = "{}/config/_set".format(hv)
    if "OaiPmhETL.rangeTo" not in hvConfig.keys():
        hvConfig["OaiPmhETL.rangeTo"] = config["hvRangeTo"]
    neutConfig = loadHvConfig(os.path.join(config["hvConfigDir"], "neut.config.json"))
    # neutralize parameters since Harvester do not care about meaningful order to change params
    try:
        r = requests.post(hvUrl, data=json.dumps(neutConfig), headers=headers)
        logger.debug("Neutralizing difficult hv params: {} {}".format(r.status_code, r.reason))
    except Exception as e:
        logger.error(e)

    try:
        r = requests.post(hvUrl, data=json.dumps(hvConfig), headers=headers)
        logger.debug("{} {}".format(r.status_code, r.reason))
    except Exception as e:
        logger.error(e)

def checkHarvester(hv):
    logger.debug("Checking harvester {}".format(hv))
    hvUrl = hv
    r = requests.get(hvUrl)
    logger.info("{} {} {}".format(r.status_code, r.reason, r.text))
    hvState = json.loads(r.text)["state"]
    hvHealth = json.loads(r.text)["health"]
    logger.info("Harvester state: {} - health {}".format(hvState, hvHealth))
    return (hvState, hvHealth)

def startHarvester(hv):
    hvUrl = hv
    r = requests.post(hvUrl)
    logger.debug("{} {} {}".format(r.status_code, r.reason, r.text))

def unloadHarvester(hvIdx, config, target):
    command =  config["hvUnloadCmd"].format(config["hvUnloadSrc"][hvIdx],target)
    logger.debug("unload harvester {} with {}".format(config["hvs"][hvIdx], command))
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
