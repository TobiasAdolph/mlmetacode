import hashlib
import json
import math
import numpy as np
import os
import pickle
import random
import re

def loadConfig(path="config.json"):
    """Loads the file with all configuration

        The config will be hashed. If there is no copy named <hash>.json 
        in the directory of the config, it will be created.

    # Argument
        path: string path to the configuration file

    # Returns
        A dict with all configuration values
    """
    with open(path, "r") as cf:
        config = json.load(cf)

    configHash = getDictHash(config)
    configBasePath = os.path.dirname(path)
    copyOfConfig = os.path.join(configBasePath, configHash + ".json")
    
    if not os.path.isfile(copyOfConfig):
        with open(copyOfConfig, "w") as f:
            json.dump(config, f)
            
    # Derived values
    config["hash"] = configHash
    config["rawDataDir"] = os.path.join(config["baseDir"], config["dtype"])
    config["processedDataDir"] = os.path.join(config["baseDir"], config["hash"])
    config["configDir"] = os.path.join(configBasePath)
    
    if not os.path.isdir(config["processedDataDir"]):
        os.mkdir(config["processedDataDir"])
    for subdir in ["retrieve", "clean", "sample", "train", "evaluate", "use"]:
        subdirPath = os.path.join(config["processedDataDir"], subdir)
        if not os.path.isdir(subdirPath):
            os.mkdir(subdirPath)

    return config

def getDictHash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

def loadJsonFromFile(config, name, subpath=""):
    paths = [
            os.path.join(config["processedDataDir"], subpath, name),
            os.path.join(config["rawDataDir"], subpath, name),
            os.path.join(config["configDir"], subpath, name) ]
    for path in paths:
        if os.path.isfile(path):
            with open(path, "r") as f:
                return json.load(f)
    raise FileNotFoundError("{} was not found in any search path of config {}".format(
        name,
        config["hash"]))

def dumpJsonToFile(config, name, payload, subpath=None): 
    path = os.path.join(config["processedDataDir"], subpath, name)
    with open(path, "w") as f:
        json.dump(payload, f)

def dumpBinary(config, obj, name, subpath=""):
    with open(os.path.join(config["processedDataDir"], subpath, name), "wb") as f:
        pickle.dump(obj, f)

def loadBinary(config, name, subpath=""):
    with open(os.path.join(config["processedDataDir"], subpath, name), "rb") as f:
        return pickle.load(f)

def loadBinaryOrNone(config, name, subpath=""):
    if os.path.isfile(os.path.join(config["processedDataDir"], subpath, name)):
        return loadBinary(config, name, subpath)
    return None

def loadTextLabelsOrEmpty(config, name):
    try:
        data = loadJsonFromFile(config, name, "train")
        return (data[0], data[1])
    except FileNotFoundError:
        return ([], [])

def loadTextAndLabels(config):
    """Loads text and labels from the rawDataDir specified in config

    # Arguments
        config: dict, configuration

    # Returns
        A dictionary with labels as keys and a list of texts as values
    """
    data = {}
    dataFilesRegex = re.compile('([0-9]{2})\.data\.json$')
    for f in os.listdir(config["rawDataDir"]):
        m = re.match(dataFilesRegex, f)
        if m:
            category = int(m.group(1)) - 1
            data[category] = []
            with open(os.path.join(config["rawDataDir"], f)) as df:
                dataFromFile = json.load(df)
            for key, value in dataFromFile.items():
                payload = []
                for modeKey in config["dmode"].split("_"):
                    payload.append(value[modeKey])
                data[category].append(" ".join(payload))
    return data

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
            last_train_item_idx = math.floor(len(data[category]) * config["ratio1"])
            last_val_item_idx = math.floor(len(data[category]) * config["ratio2"])
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
    with open(os.path.join(config["configDir"], "anzsrc.json"), "r") as f:
        return json.load(f)

def getAnzsrcAsList(config):
    retval = []
    anzsrc = getAnzsrc(config)
    for i in range(0, len(anzrc)):
        retval.append(anzsrc["{:02}".format(i)])
    return retval

def getShortAnzsrc(config):
    with open(os.path.join(config["configDir"], "shortAnzsrc.json"), "r") as f:
        return json.load(f)

def getShortAnzsrcAsList(config):
    retval = []
    shortAnzsrc = getShortAnzsrc(config)
    for i in range(0, len(shortAnzsrc)):
        retval.append(shortAnzsrc["{}".format(i)])
    return retval

def convertCfmAbsToPerc(cfm):
    newCfm = []
    for row in cfm:
        newRow = []
        rowSum = np.sum(row)
        for col in row:
            newRow.append(col/rowSum)
        newCfm.append(newRow)
    return np.array(newCfm)
