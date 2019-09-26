import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from scipy.sparse import load_npz
from util.util import loadConfig, getDictHash, setupLogging
from sklearn.metrics import precision_score, recall_score, fbeta_score, precision_recall_fscore_support
import pandas as pd
import numpy as np
from importlib import import_module
import argparse
import datetime
import re
from random import randint
from pprint import pformat
from evaluateWrappers import MLPClassifier, LSTMClassifier
import vectorize.vectorizeHelpers as vectorizeHelpers
from keras.preprocessing.sequence import pad_sequences
import json
from joblib import dump
import tensorflow as tf
import binascii

class EvaluateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(EvaluateEncoder, elsf).default(obj)

def prepare():
    parser = argparse.ArgumentParser(
        description='EVALUATE a model/param_grid/data bundle'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'evaluate'")
    parser.add_argument('--device',
            default="default",
            help = "Device name used to train the models")

    args = parser.parse_args()
    config = loadConfig(args.config)
    print("Starting with config {}\n\ttail -f {}".format(
        config["evaluate"]["hash"],
        config["evaluate"]["logFile"]
    ))
    config["logger"] = setupLogging(config, "evaluate")
    config["device"] = args.device
    if config["device"] == "default":
        prefix = "0"
    else:
        prefix = "1"
    config["target"] = os.path.join(config["evaluate"]["baseDir"], prefix + "_evaluation.csv")
    config["srcDir"] = os.path.join(
        config["vectorize"]["baseDir"],
        config["evaluate"]["vectorizeHash"]
    )

    return config

if __name__ == "__main__":
    config = prepare()
    results = []
    df = pd.DataFrame()
    if os.path.exists(config["target"]):
        df = pd.read_csv(config["target"])
        
    ########################################
    # LOAD DATA
    ########################################
    config["logger"].info("Starting to load vectorized data from {}".format(
        config["srcDir"]
    ))
    # Bag of Words
    x_train_bow = load_npz(os.path.join(config["srcDir"],"x_train_bow.npz"))
    x_test_bow = load_npz(os.path.join(config["srcDir"], "x_test_bow.npz"))
    x_train_train_bow = load_npz(os.path.join(config["srcDir"], "x_train_train_bow.npz"))
    x_train_val_bow = load_npz(os.path.join(config["srcDir"], "x_train_val_bow.npz"))
    vectorizer = vectorizeHelpers.loadBinary(config, "vectorizer.bin")
    selector = vectorizeHelpers.loadBinary(config, "selector.bin")

    # Embeddings
    x_test_emb = np.load(os.path.join(config["srcDir"], "x_test_emb.npy"))
    x_train_train_emb = np.load(os.path.join(config["srcDir"], "x_train_train_emb.npy"))
    x_train_val_emb = np.load(os.path.join(config["srcDir"], "x_train_val_emb.npy"))
    tokenizer = vectorizeHelpers.loadBinary(config, "tokenizer.bin")
    embedding_matrix = np.load(os.path.join(config["srcDir"], "embedding_matrix.npy"))

    # Labels
    y_train = load_npz(os.path.join(config["srcDir"], "y_train.npz"))
    y_test = load_npz(os.path.join(config["srcDir"], "y_test.npz"))
    y_train_train = load_npz(os.path.join(config["srcDir"], "y_train_train.npz"))
    y_train_val = load_npz(os.path.join(config["srcDir"], "y_train_val.npz"))

    # Class Weights
    label_frequency = np.sum(y_train.toarray(), axis = 0)
    config["class_weight"] = np.apply_along_axis(
            lambda x: 1/(x/max(label_frequency)), 0, label_frequency
    )

    # Wikipedia test data
    with open(os.path.join(config["evaluate"]["configDir"], "test.json"), "r") as f:
        wiki_data = json.load(f)
    x_wiki_bow = selector.transform(vectorizer.transform(wiki_data)).astype(np.float64)
    x_wiki_emb = pad_sequences(
        tokenizer.texts_to_sequences(wiki_data),
        maxlen=config["vectorize"]["maxlen"]
    )

    config["logger"].info("Finished loading data. Using these class weights {}".format(
        pformat(config["class_weight"], indent=2))
    )

    for m in config["evaluate"]["models"]:
        ########################################
        # PREPARE AND FIT THE MODEL 
        ########################################
        if m["type"] == "classic":
            module = import_module(m["package"])
            class_ = getattr(module, m["name"])
            model = class_()
        elif m["type"] == "tf_mlp":
            model = MLPClassifier()
        elif m["type"] == "tf_nlp":
            model = LSTMClassifier(tokenizer, embedding_matrix, config["vectorize"]["maxlen"])
        for key, value in m["params"].items(): 
            setattr(model, key, value)
        config["logger"].info("Starting evaluate model {}".format(m["name"]))

        if m["params"].get("seed_random_state", False):
            m["params"]["random_state"] = randint(0,2**32-1)
            setattr(model, "random_state", m["params"]["random_state"])
            config["logger"].info("Seeded random state: {}".format(m["params"]["random_state"]))
        
        pHash = getDictHash(m["params"])

        # Do not add weights to pHash
        if m["params"].get("class_weight", False):
            class_weight = config["class_weight"]
            if m["name"] in ("RandomForestClassifier", "DecisionTreeClassifier", "ExtraTreeClassifier"):
                class_weight = [{0: 1, 1: x} for x in config["class_weight"]]
            setattr(model, "class_weight", class_weight)

        config["logger"].info("Model {} with pHash {} prepared".format(m["name"], pHash))
        if len(df) > 0 and len(df[df.pHash == pHash][df.model == m["name"]]) > 0:
            config["logger"].info(
                "Model {} with pHash {} has already been evaluated!".format(
                    m["name"],
                    pHash
                )
            )
            continue

        x_test = x_test_bow
        x_wiki = x_wiki_bow
        history = {}

        if m["type"] == "classic":
            if not m["multilabel"]:
                from sklearn.multiclass import OneVsRestClassifier
                model = OneVsRestClassifier(model)
            model.fit(x_train_bow, y_train.toarray())
        elif m["type"] == "tf_mlp":
            if config["device"] != "default":
                with tf.device(config["device"]):
                    history = model.fit(x_train_train_bow, y_train_train, x_train_val_bow, y_train_val).history
            else:
                history = model.fit(x_train_train_bow, y_train_train, x_train_val_bow, y_train_val).history
        elif m["type"] == "tf_nlp":
            if config["device"] != "default":
                with tf.device(config["device"]):
                    history = model.fit(
                        x_train_train_emb,
                        y_train_train,
                        x_train_val_emb,
                        y_train_val
                    ).history
            else:
                history = model.fit(
                    x_train_train_emb,
                    y_train_train,
                    x_train_val_emb,
                    y_train_val
                ).history
            x_test = x_test_emb
            x_wiki = x_wiki_emb

        if m["type"] == "tf_nlp" or m["type"] == "tf_mlp": 
            config["logger"].info("Saving Model {} with pHash {}".format(m["name"], pHash))
            with open(os.path.join(config["evaluate"]["baseDir"], pHash + ".json"), "w") as f:
                f.write(model.to_json())
            model.save_weights(os.path.join(config["evaluate"]["baseDir"], pHash + ".h5"))
            with open(os.path.join(config["evaluate"]["baseDir"], pHash + "_history.json"), "w") as f:
                json.dump(history, f, cls=EvaluateEncoder)
        else:
            dump(model,os.path.join(config["evaluate"]["baseDir"], pHash + ".joblib"))
        config["logger"].info("Evaluate Model {} with pHash {}".format(m["name"], pHash))

        ########################################
        # CREATE PERFORMANCE REPORT
        ########################################
        config["logger"].info(
                "Successfully fitted the model, starting to create performance report"
        )
        row = {
                "model": m["name"],
                "pHash": pHash,
                "params": m["params"],
                "vHash": config["vectorize"]["hash"],
                "date": datetime.datetime.utcnow().isoformat()
        }

        y_pred = model.predict(x_test)
        y_wiki = model.predict(x_wiki)
        
        ####################
        # AVERAGE SCORES
        ####################
        row["precision_all_macro"] = precision_score(y_test, y_pred, average="macro")  
        row["precision_all_micro"] = precision_score(y_test, y_pred, average="micro")  
        row["recall_all_macro"] = recall_score(y_test, y_pred, average="macro")  
        row["recall_all_micro"] = recall_score(y_test, y_pred, average="micro")  
        row["fhalf_all_macro"] = fbeta_score(y_test, y_pred, beta=0.5, average="macro")  
        row["fhalf_all_micro"] = fbeta_score(y_test, y_pred, beta=0.5, average="micro")  
        row["fone_all_macro"] = fbeta_score(y_test, y_pred, beta=1, average="macro")  
        row["fone_all_micro"] = fbeta_score(y_test, y_pred, beta=1, average="micro")  
        row["ftwo_all_macro"] = fbeta_score(y_test, y_pred, beta=2, average="macro")  
        row["ftwo_all_micro"] = fbeta_score(y_test, y_pred, beta=2, average="micro")  
        row["wiki_diag"] = sum(np.diag(y_wiki))/y_wiki.shape[1]
        row["wiki_total"] = sum(sum(y_wiki))/y_wiki.shape[1]

        ####################
        # LABEL SCORES 
        ####################
        pcfs = precision_recall_fscore_support(y_test, y_pred, beta=1)
        for label in range(0, y_test.shape[1]):
            row["precision_" + str(label)] = pcfs[0][label]
            row["recall_" + str(label)] = pcfs[1][label]
            row["fone_" + str(label)] = pcfs[2][label]
            row["wiki_" + str(label)] = y_wiki[label][label]

        label_scores_half = fbeta_score(y_test, y_pred, beta=0.5, average=None)
        for label in range(0, y_test.shape[1]):
            row["fhalf_" + str(label)] = label_scores_half[label]

        label_scores_two = fbeta_score(y_test, y_pred, beta=2, average=None)
        for label in range(0, y_test.shape[1]):
            row["ftwo_" + str(label)] = label_scores_two[label]

        df = df.append(pd.Series(row), ignore_index=True)
        df.to_csv(config["target"], index=False)
        config["logger"].info(
                "Stored information of evaluation run to\n\t{}".format(config["target"])
        )
