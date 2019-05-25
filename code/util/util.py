import hashlib
import json
import logging
import math
import os
import pickle
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
    logger.setLevel(logging.DEBUG)
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

def loadJsonFromFile(config, name, subpath=""):
    """Wrapper around json.load() (probably bad practice)

    Searches for name in processedDataDir, inputDataDir and configDir, as given
    by config.

    # Arguments
        config:  a dictionary with the paths to search
        name:    name of the file to load
        subpath: optional, allows to specifiy a subpath under the pathes
                 configured in config
    # Returns
        The loaded json as a python data structure
    """
    paths = [
            os.path.join(config["processedDataDir"], subpath, name),
            os.path.join(config["inputDataDir"], subpath, name),
            os.path.join(config["configDir"], subpath, name) ]
    for path in paths:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return json.load(f)
    raise FileNotFoundError("{} was not found in any search path of config {}".format(
        name,
        config["hash"]))

def dumpJsonToFile(config, name, payload, subpath=""):
    """ Wrapper around json.dump() (probably bad practice) dumps a given datastructure

    # Arguments:
        config:  a dictionary with the processedDataDir path to dump to
        name:    name of the file to be dumped
        payload: python datastructure to be dumped
        subpath: optional, allows to specifiy a subpath under processedDataDir
    """
    path = os.path.join(config["processedDataDir"], subpath, name)
    with open(path, "w") as f:
        json.dump(payload, f)

def dumpBinary(config, name, payload):
    """ Wrapper around pickle.dump() dumps an python object

    # Arguments:
        config:  a dictionary with the processedDataDir path to dump to
        name:    name of the file to be dumped
        payload: python object to be dumped
    """
    with open(os.path.join(config["vectorize"]["outputDir"], name), "wb") as f:
        pickle.dump(payload, f)

def loadBinary(config, name):
    """Wrapper around pickle.load()

    # Arguments
        config:  a dictionary with the paths to search
        name:    name of the file to load

    # Returns
        The loaded binary as a python data structure
    """
    with open(os.path.join(config["vectorize"]["outputDir"], name), "rb") as f:
        return pickle.load(f)

def loadTextLabelsOrEmpty(config, name):
    """ Check whether the text and labels are already sampled and load them

    # Arguments
        config: a dictionary with the path to search for the samples
        name: name of the sample part (train|val|test).json
    """
    try:
        data = loadJsonFromFile(config, name, "train")
        return (data[0], data[1])
    except FileNotFoundError:
        return ([], [])

def loadSample(config, data=None, save=True):
    """Loads text and labels and splits it into train/validate/test sets.

    The call uses stored files if they exist.

    # Arguments
        config: dict, config hash

    # Returns
        A triple of tuples of text and labels (train, val and test)

    # References
        Inspired by
        https://developers.google.com/machine-learning/guides/text-classification/step-2
    """

    #TODO input validation: config["ratio1"] + ratio2 (< 1, > 0, ratio2 > config["ratio1"])
    # Split:
    # 3. split it into train/val/test sets
    # 4. Save + re-use the specific sets

    # Load already prepared files
    (train_texts, train_labels) = loadTextLabelsOrEmpty(config, "train.json")
    (val_texts, val_labels) = loadTextLabelsOrEmpty(config, "val.json")
    (test_texts, test_labels) = loadTextLabelsOrEmpty(config, "test.json")

    if not (train_texts and val_texts and test_texts):
        if not data:
            data = loadTextAndLabels(config)
        for category in data.keys():
            random.shuffle(data[category])
            last_train_item_idx = math.floor(len(data[category]) *
                                             config["ratio1"]) - 1
            last_val_item_idx = math.floor(len(data[category]) *
                                           config["ratio2"]) - 1
            #print("category: {} size: {} train until: {} val until: {}".format(
            #    category, len(data[category]), last_train_item_idx, last_val_item_idx))

            for idx, payload in enumerate(data[category]):
                if idx <= last_train_item_idx:
                    train_texts.append(payload)
                    train_labels.append(category)
                elif idx <= last_val_item_idx:
                    val_texts.append(payload)
                    val_labels.append(category)
                else:
                    test_texts.append(payload)
                    test_labels.append(category)
        random.seed(config["seed"])
        random.shuffle(train_texts)
        random.seed(config["seed"])
        random.shuffle(train_labels)

    if save:
        dumpJsonToFile(config, "train.json", [train_texts, train_labels], "train")
        dumpJsonToFile(config, "val.json", [val_texts, val_labels], "train")
        dumpJsonToFile(config, "test.json", [test_texts, test_labels], "train")

    return ((train_texts, np.array(train_labels)),
            (val_texts, np.array(val_labels)),
            (test_texts, np.array(test_labels))
    )

def getAnzsrc(config):
    """ Get a dictionary mapping a label (number) to the names of the disciplines
    (physical science)

    # Argument
        config: a dictionary with the necessary path information

    # Returns
        a dictionary with keys (01) mapping to names (physical science)
    """
    with open(os.path.join(config["base"]["configDir"], "anzsrc.json"), "r") as f:
        return json.load(f)

def getAnzsrcAsList(config):
    """ Get a list of disciplines with a label - 1 (number -1) mapping to the
    name of the disciplines.

    # Argument
        config: a dictionary with the necessary path information

    # Returns
        a python list (idx + 1 is the idx of the discipline)
    """
    retval = []
    anzsrc = getAnzsrc(config)
    for i in range(0, len(anzsrc)):
        retval.append(anzsrc["{:02}".format(i)])
    return retval

def getShortAnzsrc(config):
    """ Get a dictionary mapping a label (number) to the short names of the disciplines
    (physical science)

    # Argument
        config: a dictionary with the necessary path information

    # Returns
        a dictionary with keys (01) mapping to names (physical science)
    """
    with open(os.path.join(config["base"]["configDir"], "shortAnzsrc.json"), "r") as f:
        return json.load(f)

def getShortAnzsrcAsList(config):
    """ Get a list of disciplines with a label - 1 (number -1) mapping to the
    short name of the disciplines.

    # Argument
        config: a dictionary with the necessary path information

    # Returns
        a python list (idx + 1 is the idx of the discipline) 
    """
    retval = []
    shortAnzsrc = getShortAnzsrc(config)
    for i in range(0, len(shortAnzsrc)):
        retval.append(shortAnzsrc["{}".format(i)])
    return retval


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
