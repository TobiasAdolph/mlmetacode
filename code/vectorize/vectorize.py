import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import json
import re
import util.util as util
import vectorizeHelpers
import glob
import pandas as pd
import numpy as np
import scipy.sparse
from sklearn.model_selection import train_test_split
from random import randint
import nltk

def prepare():
    parser = argparse.ArgumentParser(
        description='VECTORIZE the sampled data'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'vectorize'")

    args = parser.parse_args()
    config = util.loadConfig(args.config)
    print("Starting vectorize with config {}".format(config["vectorize"]["hash"]))
    config["logger"] = util.setupLogging(config, "vectorize")
    config["src"] = os.path.join(config["clean"]["baseDir"],
                 config["vectorize"]["cleanHash"],
                "useable.csv"
    )
    config["labels"] = util.getLabels(config)[1:]
    config["stop_words"] = util.getStopWords(config)
    stopWordsHash = util.getDictHash(config["stop_words"])
    if stopWordsHash != config["vectorize"]["stopWordsHash"]:
        config["logger"].error("Hash of used and configured stop words differ:"
                               "\n\t{} (used)"
                               "\n\t{} (configured)"
                               "\n\tRestore old stop word list or change config".format(
                                   stopWordsHash ,
                                   config["vectorize"]["stopWordsHash"]
                               )
        )
        os.sys.exit(1)

    if config["vectorize"]["stemming"] == "none":
        config["payload"] = "payload"
    else:
        config["payload"] = config["vectorize"]["stemming"]
    return config

if __name__ == "__main__":
    config = prepare()
    info = { "seed" : config["vectorize"].get("seed", randint(0,2**32-1)) }
    df = pd.read_csv(config["src"], index_col=0)

    ########################################  
    # SPLIT
    ########################################
    config["logger"].info("Splitting {} with seed {}".format(config["src"], info["seed"]))
    # we need to recalculate, because pandas saves the lists as strings.
    df['labelsI'] = df.labels.apply(lambda x: util.int2bv(x, 21)[1:]).tolist()
    df_train, df_test = (train_test_split(
        df,
        random_state=info["seed"],
        test_size=config["vectorize"]["test_size"],
        shuffle = True,
        stratify=df.bl
    ))
    df_train.to_csv(os.path.join(config["vectorize"]["outputDir"], "train.csv"))
    df_test.to_csv(os.path.join(config["vectorize"]["outputDir"], "test.csv"))
    info["noTrain"] = len(df_train)
    info["noTest"] = len(df_test) 

    df_train_train, df_train_val = (train_test_split(
        df,
        random_state=info["seed"],
        test_size=config["vectorize"]["test_size"],
        shuffle = True,
        stratify=df.bl
    ))
    df_train_train.to_csv(os.path.join(config["vectorize"]["outputDir"], "train_train.csv"))
    df_train_val.to_csv(os.path.join(config["vectorize"]["outputDir"], "train_val.csv"))
    info["noTrain_train"] = len(df_train_train)
    info["noTrain_val"] = len(df_train_val)

    ########################################  
    # VECTORIZE
    ######################################## 
    config["logger"].info("Vectorizing {}".format(config["src"]))

    ####################
    # BAG OF WORDS
    ####################
    (vectorizer, selector, x) = vectorizeHelpers.getVectorizerAndSelector(config, df_train)
    with open(os.path.join(config["vectorize"]["outputDir"], "vocab_scores.json"), "w") as f:
        json.dump(vectorizeHelpers.getSelectedVocabularyAndScores(vectorizer.vocabulary_, selector),f)
    info["allFeatures_bow"] = x.shape[1]
    x_train_bow = selector.transform(x).astype(np.float64)
    info["selectedFeatures_bow"] = x_train_bow.shape[1]
    x_test_bow = selector.transform(vectorizer.transform(df_test[config["payload"]])).astype(np.float64)
    x_train_train_bow = selector.transform(vectorizer.transform(df_train_train[config["payload"]])).astype(np.float64)
    x_train_val_bow = selector.transform(vectorizer.transform(df_train_val[config["payload"]])).astype(np.float64)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_train_bow"), x_train_bow)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_test_bow"), x_test_bow)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_train_train_bow"), x_train_train_bow)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_train_val_bow"), x_train_val_bow)
    vectorizeHelpers.dumpBinary(config, "vectorizer.bin", vectorizer)
    vectorizeHelpers.dumpBinary(config, "selector.bin", selector)

    ####################
    # EMBEDDINGS
    ####################
    x_train_emb = vectorizeHelpers.vectorizeEmbeddings(config, df_train)
    x_test_emb = vectorizeHelpers.vectorizeEmbeddings(config, df_test)
    x_train_train_emb = vectorizeHelpers.vectorizeEmbeddings(config, df_train_train)
    x_train_val_emb = vectorizeHelpers.vectorizeEmbeddings(config, df_train_val) 
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_train_emb"), x_train_emb)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_test_emb"), x_test_emb)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_train_train_emb"), x_train_train_emb)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_train_val_emb"), x_train_val_emb)

    ####################
    # LABELS 
    ####################
    y_train = scipy.sparse.csc_matrix(df_train.labelsI.values.tolist())
    y_test = scipy.sparse.csc_matrix(df_test.labelsI.values.tolist())
    y_train_train = scipy.sparse.csc_matrix(df_train_train.labelsI.values.tolist())
    y_train_val = scipy.sparse.csc_matrix(df_train_val.labelsI.values.tolist())
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "y_train"), y_train)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "y_test"), y_test)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "y_train_train"), y_train_train)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "y_train_val"), y_train_val) 

    with open(os.path.join(config["vectorize"]["outputDir"], "info.json"), "w") as f:
        json.dump(info,f)
