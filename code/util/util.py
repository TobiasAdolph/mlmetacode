import json
import math
import numpy as np
import os
import pickle
import random
import re

def loadConfig(path="config.json"):
    """Loads the file with all configuration

    # Argument
        path: string path to the configuration file

    # Returns
        A dict with all configuration values
    """
    with open(path, "r") as cf:
        config = json.load(cf)

    config["dataDir"] = os.path.join(config["baseDir"], config["dtype"])
    return config

def loadJsonFromFile(config, name):
    path = os.path.join(config["dataDir"], name)
    with open(path, "r") as f:
        return json.load(f)

def dumpJsonToFile(config, name, payload): 
    path = os.path.join(config["dataDir"], name)
    with open(path, "w") as f:
        json.dump(payload, f)

def dumpBinary(config, obj, name):
    with open(os.path.join(config["dataDir"], name), "wb") as f:
        pickle.dump(obj, f)

def loadBinary(config, name):
    with open(os.path.join(config["dataDir"], name), "rb") as f:
        return pickle.load(f)

def loadBinaryOrNone(config, name):
    if os.path.isfile(os.path.join(config["dataDir"], name)):
        return loadBinary(config, name)
    return None

def loadTextLabelsOrEmpty(config, name):
    path = os.path.join(config["dataDir"], name)
    if os.path.isfile(path):
        data = loadJsonFromFile(config, name)
        return (data[0], data[1])
    else:
        return ([], [])

def loadSample(config, save=True):
    """Loads a sample of titles/descriptions uses stored files if exist.

    # Arguments
        config: dict, config hash

    # Returns
        A triple of tuples of text and labels (train, val and test)

    # References
        Inspired by 
        https://developers.google.com/machine-learning/guides/text-classification/step-2
    """

    #TODO input validation: config["ratio1"] + ratio2 (< 1, > 0, ratio2 > config["ratio1"]) 

    # Load already prepared files
    (train_texts, train_labels) = loadTextLabelsOrEmpty(config, "train.json")
    (val_texts, val_labels) = loadTextLabelsOrEmpty(config, "val.json")
    (test_texts, test_labels) = loadTextLabelsOrEmpty(config, "test.json") 

    if not (train_texts and val_texts and test_texts):
        dataRegex = re.compile('([0-9]{2})\.data\.json$')
        for f in os.listdir(config["dataDir"]):
            m = re.match(dataRegex, f)
            if m:
                category = int(m.group(1)) - 1
                with open(os.path.join(config["dataDir"], f)) as df:
                    data = json.load(df)
                keys = list(data.keys())
                random.shuffle(keys)
                last_train_item_idx = math.floor(len(data) * config["ratio1"])
                last_val_item_idx = math.floor(len(data) * config["ratio2"])
                for idx, key in enumerate(keys):
                    payload = []
                    for modeKey in config["dmode"].split("_"):
                        payload.append(data[key][modeKey])
                    payload = " ".join(payload)
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
        dumpJsonToFile(config, "train", [train_texts, train_labels])
        dumpJsonToFile(config, "val", [val_texts, val_labels])
        dumpJsonToFile(config, "test", [test_texts, test_labels])

    return ((train_texts, np.array(train_labels)),
            (val_texts, np.array(val_labels)),
            (test_texts, np.array(test_labels))
    )
