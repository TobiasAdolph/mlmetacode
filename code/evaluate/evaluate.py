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

def prepare():
    parser = argparse.ArgumentParser(
        description='EVALUATE a model/param_grid/data bundle'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'evaluate'")

    args = parser.parse_args()
    config = loadConfig(args.config)
    print("Starting with config {}\n\ttail -f {}".format(
        config["evaluate"]["hash"],
        config["evaluate"]["logFile"]
    ))
    config["logger"] = setupLogging(config, "evaluate")
    config["target"] = os.path.join(config["evaluate"]["baseDir"], "evaluation.csv")
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
        df = pd.read_csv(config["target"], index_col=0)
        
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
    x_test_emb = load_npz(os.path.join(config["srcDir"], "x_test_emb.npz")).toarray()
    x_train_train_emb = load_npz(os.path.join(config["srcDir"], "x_train_train_emb.npz")).toarray()
    x_train_val_emb = load_npz(os.path.join(config["srcDir"], "x_train_val_emb.npz")).toarray()
    tokenizer = vectorizeHelpers.loadBinary(config, "tokenizer.bin")
    embedding_matrix = load_npz(os.path.join(config["srcDir"], "embedding_matrix.npz"))

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
            model = LSTMClassifier(tokenizer, embedding_matrix)
        for key, value in m["params"].items(): 
            setattr(model, key, value)
        config["logger"].info("Starting evaluate model {}".format(m["name"]))
        if m["params"].get("class_weight", False):
            class_weight = config["class_weight"]
            if m["name"] in ("RandomForestClassifier", "DecisionTreeClassifier", "ExtraTreeClassifier"):
                class_weight = [{0: 1, 1: x} for x in config["class_weight"]]
            setattr(model, "class_weight", class_weight)
        pHash = getDictHash(m["params"])
        if not getattr(model, "random_state", False):
            if len(df[df.pHash == pHash][df.model == m["name"]]) > 0:           
                config["logger"].info(
                    "Model {} with pHash {} has already been evaluated!".format(
                        m["name"],
                        pHash
                    )
                )
                continue
        else:
            m["params"]["random_state"] = randint(0,2**32-1)
            pHash = getDictHash(m["params"])
            config["logger"].info(
                "Evaluate Model {} with pHash {} and random state {}".format(
                    m["name"],
                    pHash,
                    m["params"]["random_state"]
                )
            )

        x_test = x_test_bow
        x_wiki = x_wiki_bow
        if m["type"] == "classic":
            if not m["multilabel"]:
                from sklearn.multiclass import OneVsRestClassifier
                model = OneVsRestClassifier(model)
            model.fit(x_train_bow, y_train.toarray())
        elif m["type"] == "tf_mlp":
            model.fit(x_train_train_bow, y_train_train, x_train_val_bow, y_train_val)
        elif m["type"] == "tf_nlp": 
            model.fit(
                x_train_train_emb,
                y_train_train,
                x_train_val_emb,
                y_train_val
            )
            x_test = x_test_emb.toarray()
            x_wiki = x_wiki_emb

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

        results.append(row)
        cur_df = pd.DataFrame(results)
        if len(df) == 0:
            df = cur_df
        else:
            df = pd.concat([df, cur_df], sort=False)
        df.to_csv(config["target"])
        config["logger"].info(
                "Stored information of evaluation run to\n\t{}".format(config["target"])
        )
