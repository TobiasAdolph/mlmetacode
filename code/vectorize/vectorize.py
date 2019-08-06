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
from nltk.stem.lancaster import LancasterStemmer
from nltk.stem.porter import PorterStemmer
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
    config["logger"] = util.setupLogging(config, "vectorize")
    config["src"] = os.path.join(config["clean"]["baseDir"],
                 config["vectorize"]["cleanHash"],
                "useable.csv"
    )
    config["labels"] = util.getLabels(config)[1:]
    return config

if __name__ == "__main__":
    config = prepare()
    print("Starting vectorize with config {}".format(config["vectorize"]["hash"]))
    df = pd.read_csv(config["src"], index_col=0)
    if config["vectorize"]["stemming"] != "none":
        nltk.download('punkt')
        if config["vectorize"]["stemming"] == "lancaster":
            stemmer = LancasterStemmer()
        if config["vectorize"]["stemming"] == "porter":
            stemmer = PorterStemmer()
        df['payload'] = df.payload.apply(lambda x: vectorizeHelpers.stem(x, stemmer))
        config["vectorize"]["stop_words"] = (
            [vectorizeHelpers.stem(stop_word, stemmer) for stop_word in ( 
                config["vectorize"]["stop_words"])])
    # for convenience: convert labels in in bitvector to one hot encoding
    df['labelsI'] = df.labels.apply(lambda x: util.int2bv(x, 21)[1:]).tolist()
    disciplineCounts = util.getDisciplineCounts(config, df)
    disciplineCounts.to_csv(os.path.join(config["vectorize"]["outputDir"], "disciplineCounts.csv"))
    # determine best label (bl) for each record
    ssf = pd.Series(np.diag(disciplineCounts))
    df['bl'] = df.labelsI.apply(lambda x: util.getBestLabel(ssf, x))
    df.to_csv(os.path.join(config["vectorize"]["outputDir"], 'useable.csv'))
    config["logger"].info("Vectorizing {}".format(config["src"]))
    (vectorizer, selector, x) = vectorizeHelpers.getVectorizerAndSelector(config, df)
    xSelected =  selector.transform(x).astype(np.float64)
    with open(os.path.join(config["vectorize"]["outputDir"], "vocab_scores.json"), "w") as f:
        json.dump(vectorizeHelpers.getSelectedVocabularyAndScores(vectorizer.vocabulary_, selector),f)

    seed = randint(0,2**32-1)

    x_train, x_test, y_train, y_test = (
        train_test_split(
            xSelected,
            df.labelsI.values.tolist(),
            random_state=seed,
            test_size=config["vectorize"]["test_size"],
            shuffle = True,
            stratify=df.bl,
        ))
    config["logger"].info("Split with seed {}".format(seed))
    y_train = scipy.sparse.csc_matrix(y_train)
    y_test = scipy.sparse.csc_matrix(y_test)

    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_train"), x_train)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "y_train"), y_train)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "x_test"), x_test)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], "y_test"), y_test)
    vectorizeHelpers.dumpBinary(
        config,
        "vectorizer.bin",
        vectorizer)
    vectorizeHelpers.dumpBinary(
        config,
        "selector.bin",
        selector)
