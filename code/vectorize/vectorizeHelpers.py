import numpy as np
import pandas as pd
import json
import os
import re
import pickle
import scipy.sparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_classif

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

def getVectorizerAndSelector(config, corpus):
    kwargs = {
            'ngram_range': config["vectorize"]["ngramRange"],
            'dtype': config["vectorize"]["dtype"],
            'strip_accents': 'unicode',
            'decode_error': 'replace',
            'analyzer': config["vectorize"]["tokenMode"],
            'min_df': config["vectorize"]["minDocFreq"]
    }
    vectorizer =  TfidfVectorizer(**kwargs)
    x = vectorizer.fit_transform(corpus["payload"])
    selector = SelectKBest(f_classif, k=min(config["vectorize"]["topK"], x.shape[1]))
    # we need the labels, otherwise we cannot guarantee that the selector selects
    # something for every label ?
    selector.fit(x, corpus["label"])
    return (
        vectorizer,
        selector,
        selector.transform(x).astype(config["vectorize"]["dtype"])
    )

def vectorizeAndSave(config, corpus, selectedAs, vectorizer, selector):
    x = vectorizer.transform(corpus[corpus["selectedAs"] == selectedAs]["payload"])
    x = selector.transform(x).astype(config["vectorize"]["dtype"])
    y = corpus[corpus["selectedAs"] == selectedAs]["label"]
    saveFilePrefix = "{}".format(selectedAs)
    dataFile = saveFilePrefix + "_data.npz"
    labelsFile = saveFilePrefix + "_labels.h5"
    store = pd.HDFStore(os.path.join(config["vectorize"]["outputDir"], labelsFile))
    store["labels"] = y
    store.close()
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"], dataFile), x)
    config["logger"].info("Saved labels and payload at \n\t{} and \n\t{}".format(
        labelsFile, dataFile))
