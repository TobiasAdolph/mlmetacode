import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import numpy as np
import pandas as pd
import json
import os
import re
import util.util as util

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_classif

def loadSample(config):
    """Loads text and labels from the sample  specified in config

    # Arguments
        config: a dictionary with necessary paths

    # Returns
        A dictionary with labels as keys and a list of texts as values
    """
    texts = np.array([])
    labels = np.array([], np.int)
    for f in os.listdir(config["src"]):
        m = config["dataInputRegexCompiled"].match(f)
        if m:
            category = int(m.group(1)) - 1
            with open(os.path.join(config["src"], f)) as df:
                for key, value in json.load(df).items():
                    text = ""
                    for modeKey in config["vectorize"]["dmode"].split("_"):
                        text += " " + value[modeKey]
                    texts = np.append(texts, cleanText(config, text))
                    labels = np.append(labels, category)
    return pd.concat([pd.Series(texts, name="text"), pd.Series(labels, name="label")], axis=1)

def cleanText(config, text):
    for replacement, regex in config["regex"].items():
        text = re.sub(regex, replacement, text)
    text = re.sub("\s+", " ", text)
    if "stemmer" in config.keys():
        stems = [ config["stemmer"].stem(word) for word in text.split(" ") ]
        text = " ".join(stems)
    return text.strip().lower()


def ngramVectorize(config, corpus, save=True):
    """Vectorizes texts as n-gram vectors.

    1 text = 1 tf-idf vector the length of vocabulary of unigrams + bigrams.

    # Arguments
        config: dict, config hash
        corpus: pd.DataFrame of texts and labels
        save: Save vectorizer and selector to disk

    # Returns
        x: vectorized texts

    # References
        Adapted from
        https://developers.google.com/machine-learning/guides/text-classification/step-3
    """

    try:
        vectorizer = util.loadBinary(config, "vectorizer.bin")
    except FileNotFoundError:
        vectorizer = None

    try:
        selector = util.loadBinary(config, "selector.bin")
    except FileNotFoundError:
        selector = None

    if not vectorizer:
        kwargs = {
                'ngram_range': config["vectorize"]["ngramRange"],
                'dtype': np.float64,
                'strip_accents': 'unicode',
                'decode_error': 'replace',
                'analyzer': config["vectorize"]["tokenMode"],
                'min_df': config["vectorize"]["minDocFreq"]
        }
        vectorizer = TfidfVectorizer(**kwargs)
        x = vectorizer.fit_transform(corpus["text"])
    else:
        x = vectorizer.transform(corpus["text"])

    if not selector:
        selector = SelectKBest(f_classif, k=min(config["vectorize"]["topK"], x.shape[1]))
        # we need the labels, otherwise we cannot guarantee that the selector selects
        # something for every label ?
        selector.fit(x, corpus["label"])

    if save:
        util.dumpBinary(config, "vectorizer.bin", vectorizer)
        util.dumpBinary(config, "selector.bin", selector)

    return selector.transform(x).astype('float64')
