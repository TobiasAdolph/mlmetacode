import hashlib
import json
import logging
import math
import os
import random
import re

import numpy as np
import pandas as pd

from sklearn.metrics import confusion_matrix

def loadConfig(path="config.json"):
    """Loads the file with all configuration

        The config will be hashed. If there is no copy named <hash>.json
        in the directory of the config, it will be created. If the directory
        for processed data does not exist, it will be created.

    # Argument
        path: string path to the configuration file

    # Returns
        A dict with all configuration values
    """
    with open(path, "r") as cf:
        config = json.load(cf)

    configDir        = os.path.dirname(path)
    logDir           = os.path.join(config["base"]["dir"], "log")
    processedDataDir = os.path.join(config["base"]["dir"], "processed")

    for step in config.keys():
        stepHash = getDictHash(config[step], step)
        directories = {
            "configDir": os.path.join(configDir, step),
            "baseDir": os.path.join(processedDataDir, step),
            "outputDir": os.path.join(processedDataDir, step, stepHash),
            "logDir":    os.path.join(logDir, step, stepHash)
        }
        for dirType, dirPath in directories.items():
            createDirIfNotExists(dirPath)
        saveCopy = os.path.join(directories["configDir"], stepHash + ".json")
        if not os.path.isfile(saveCopy):
            with open(saveCopy, "w") as f:
                json.dump(config[step], f)
        config[step]["hash"] = stepHash
        for directory in directories:
            config[step][directory] = directories[directory]
        config[step]["logFile"] = os.path.join(directories["logDir"], step + ".log")

    return config

def createDirIfNotExists(path):
    if not os.path.isdir(path):
        os.makedirs(path)

def setupLogging(config, step):
    # LOGGING
    logger = logging.getLogger(step)
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(config[step]["logFile"])
    formatter = logging.Formatter('%(asctime)s|%(process)d %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

def getDictHash(payload, step=None):
    """Reproducibly sha256-hashes a python dictionary to the same hash
    value if the keys, values are identical.

    # Argument
        payload: A python dictionary

    # Returns
        A SHA256 hash
    """
    if step == "retrieve":
        basePayload = {
            "hvConfigRegex": payload["hvConfigRegex"],
            "hvRangeTo": payload["hvRangeTo"]
        }
    else:
        basePayload = payload

    return hashlib.sha256(json.dumps(basePayload, sort_keys=True).encode("utf-8")).hexdigest()

def getFileHash(filePath):
    """
        taken from https://stackoverflow.com/a/44873382
    """
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filePath, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()

def getLabels(config):
    with open(os.path.join(config["base"]["configDir"], "labels.json"), "r") as f:
        return json.load(f)

def saveJson(config, step, name, payload):
    saveLoc = os.path.join(config[step]["outputDir"], name)
    with open(saveLoc, "r") as f:
        json.dump(payload, f)

def getConfusionMatrix(config, model, test_texts, test_labels):
    """ Calculates a confusion matrix

    # Arguments
        config: a dictionary holding pathes, parameters, etc.
        model: the model to be used to predict
        test_texts: Texts to use to build the confusion matrix
        test_labels: Labels for the test

    # Returns
        a confusion matrix (np.array)
    """
    x_test = ngramVectorize(test_texts, test_labels, config, False)
    predictions = []
    for x in model.predict(x_test):
        predictions.append(np.argmax(x))
    return confusion_matrix(
            test_labels,
            predictions)

def cfm2df(cfm, labels):
    """ Converts a confusion matrix to a pandas data frame

    # Arguments
        cfm: the confusion matrix to be transformed
        labels: labels (or index) that the dataframe should have as a list

    # Returns
        a pandas data frame
    """
    df = pd.DataFrame()
    # rows
    for i, row_label in enumerate(labels):
        rowdata={}
        # columns
        for j, col_label in enumerate(labels):
            rowdata[col_label]=cfm[i,j]
        df = df.append(pd.DataFrame.from_dict({row_label:rowdata}, orient='index'))
    return df[labels]

def power_of_two(i):
    return i != 0 and ((i & (i - 1)) == 0)

def int2bv(i, length):
    bv = np.array([int(x) for x in list(bin(i))[2:]])
    return np.pad(np.flip(bv), (0,length-len(bv)), mode="constant")

def getBestLabel(ssf, labels):
    """
        Arguments
            ssf: pd.Series keeping track which label has been selected how often so far
                 (ssf = selected so far). This Series is zero-based!
            labels: Bit-Vector indicating the labels set.
                 This vectors index logically starts at 1!
    """
    # if only one label bit is set in index vector, return it
    if np.count_nonzero(labels) == 1:
        return np.nonzero(labels)[0][0] + 1
    # if more than one label bit is set:
    # 1. select the label with the least amount of occurences so far
    # 2. increase the selected counter by one
    # 3. return +1 (ssf is zero based)
    bl = ssf[np.where(labels)[0]].idxmin()
    ssf[bl] += 1
    return bl + 1

def getDisciplineCounts(config, df):
    t = np.zeros((20,20),np.int32)
    for i in range(0,20):
        label = i + 1
        for j in range(0,20):
            if j < i:
                continue
            clabel = j + 1
            mask = 0
            mask |= 1 << label
            mask |= 1 << clabel
            t[i][j] = df[df.labels & mask == mask].labels.count()
    counts = pd.DataFrame(t)
    counts.columns = range(1,21)
    rows = {i: config["labels"][i] for i in range(0, len(config["labels"]))}
    counts.rename(index=rows, inplace=True)
    return counts
