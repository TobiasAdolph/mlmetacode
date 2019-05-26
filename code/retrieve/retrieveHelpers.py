import json
import logging
import os
import random
import re
import requests
import subprocess
import sys
import time

def doHarvest(payload):
    config = payload[0]
    fileName = payload[1]
    config["logger"].info("Starting worker with config {} and fileName {}".format(
        config["retrieve"]["hash"],
        fileName
    ))
    retrievalId = config["retrieve"]["hvConfigRegexCompiled"].match(fileName).group(1)
    target = os.path.join(config["retrieve"]["outputDir"], retrievalId + ".json")
    if os.path.isfile(target):
        config["logger"].info("{} already exists, skipping".format(retrievalId))
        return True
    config["logger"].info(
        "================> do harvest with {} ({})".format(retrievalId, fileName)
    )
    hvIdx = getFreeHarvester(config)
    if not hvIdx in range(len(config["retrieve"]["hvs"])):
        config["logger"].error("Error, no hv is available: {}".format(hvIdx))
        return False

    hv = config["retrieve"]["hvs"][hvIdx]
    hvConfig = loadHvConfig(config, fileName)
    config["logger"].info(
        "Loading Harvester {} \n\tfor target {} \n\tunload to {}".format(
            hv,
            retrievalId,
            config["retrieve"]["hvUnloadSrc"][hvIdx]
        )
    )
    loadHarvester(config, hvConfig, hv)
    startHarvester(config, hv)
    hvState = "HARVESTING"
    while hvState in ["HARVESTING", "QUEUED"]:
        time.sleep(config["retrieve"]["sleep"])
        config["logger"].debug(
            "Harvester {} for {} slept {} seconds, checking harvester".format(
            hv,
            retrievalId,
            config["retrieve"]["sleep"])
        )
        (hvState, hvHealth) = checkHarvester(config, hv)
    config["logger"].info(
        "Harvester {} for {} finished with state {} and health {}".format(
            hv,
            retrievalId,
            hvState,
            hvHealth
        )
    )

    if hvState == "IDLE":
        # wait for the harvester to finalize IO of harvest
        time.sleep(5)
        unloadHarvester(config, hvIdx, target)
        returnHarvester(config, hvIdx)
        return True
    else:
        config["logger"].error("Could not unload Harvester {} for {}".format(
                hv,
                retrievalId
            )
        )
        returnHarvester(config, hvIdx)
        return False

def loadHarvester(config, hvConfig, hv):
    headers = {'Content-Type': "application/json"}
    hvUrl = "{}/config/_set".format(hv)
    hvConfig["OaiPmhETL.rangeTo"] = min(
        hvConfig.get("OaiPmhETL.rangeTo", config["retrieve"]["hvRangeTo"]),
        config["retrieve"]["hvRangeTo"]
    )
    neutConfig = loadHvConfig(
        config,
        os.path.join(config["retrieve"]["configDir"], "neut.config.json")
    )
    # neutralize parameters since Harvester do not care about
    # meaningful order to change params
    try:
        r = requests.post(hvUrl, data=json.dumps(neutConfig), headers=headers)
        config["logger"].debug(
            "Neutralizing difficult hv params: {} {}".format(r.status_code, r.reason))
    except Exception as e:
        config["logger"].error(e)
        raise

    try:
        r = requests.post(hvUrl, data=json.dumps(hvConfig), headers=headers)
        config["logger"].debug("{} {}".format(r.status_code, r.reason))
    except Exception as e:
        config["logger"].error(e)
        raise

def checkHarvester(config, hv):
    config["logger"].debug("Checking harvester {}".format(hv))
    hvUrl = hv
    r = requests.get(hvUrl)
    config["logger"].debug("{} {} {}".format(r.status_code, r.reason, r.text))
    return (
        json.loads(r.text)["state"],
        json.loads(r.text)["health"]
    )

def startHarvester(config, hv):
    hvUrl = hv
    r = requests.post(hvUrl)
    config["logger"].debug("{} {} {}".format(r.status_code, r.reason, r.text))

def unloadHarvester(config, hvIdx, target):
    command =  config["retrieve"]["hvUnloadCmd"].format(
        config["retrieve"]["hvUnloadSrc"][hvIdx], target)
    config["logger"].debug("unload harvester with {}".format(command))
    cp = subprocess.run(command.split())
    if not cp.returncode == 0:
        emptyPayload = { "documents": [] }
        with open(target, "w") as f:
            json.dump(emptyPayload, f)

def loadHvConfig(config, hvConfigPath):
    with open(hvConfigPath, "r") as f:
        return json.load(f)

def init_globals(hvs):
    global _HVS
    _HVS = hvs

def getFreeHarvester(config):
    with _HVS.get_lock():
        freeIdx = None
        for idx, isFree in enumerate(_HVS):
            if isFree:
                config["logger"].info("Using hv {}".format(idx))
                freeIdx = idx
                _HVS[idx] = False
                break
    return freeIdx

def returnHarvester(config, hvIdx):
    config["logger"].info("Returning harvester {}".format(hvIdx))
    with _HVS.get_lock():
         _HVS[hvIdx] = True
