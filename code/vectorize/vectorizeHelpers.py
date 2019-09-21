import numpy as np
import pandas as pd
import json
import os
import re
import pickle
import math
import nltk
import scipy.sparse
from nltk import util, stem
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_classif
from gensim.models import KeyedVectors
from keras.preprocessing.text import Tokenizer

from nltk.stem.lancaster import LancasterStemmer
from nltk.stem.porter import PorterStemmer

from operator import itemgetter

def getTokenizerAndEmbeddingMatrix(config, payload):
    """ Vectorize the payload in df as embeddings

    # Arguments:
        config:  a dictionary with the configuration 
        df: a pandas dataFrame with the data (key: payload)

    # Returns
        The embeddings as a sparse matrix

    # See
        vectorizeBagOfWords
    """
    tokenizer = Tokenizer(lower=config["vectorize"]["case_sensitivity"])
    tokenizer.fit_on_texts(payload)

    model = KeyedVectors.load_word2vec_format(
        os.path.join(config["vectorize"]["baseDir"], config["vectorize"]["word2vec"]),
        binary=True
    )

    embedding_matrix = np.zeros((len(tokenizer.word_index)+1, 300))
    for word, i in tokenizer.word_index.items():
        try:
            embedding_matrix[i] = model.wv[word]
        except KeyError:
            pass
    return tokenizer, embedding_matrix

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

def getVectorizerAndSelector(config, df):
    kwargs = {
            'ngram_range': config["vectorize"]["ngramRange"],
            'dtype': np.float64,
            'strip_accents': 'unicode',
            'decode_error': 'replace',
            'analyzer': config["vectorize"]["tokenMode"],
            'min_df': config["vectorize"]["minDocFreq"],
            'stop_words': config["stop_words"]
    }
    if config["vectorize"]["stemming"] != "none":
        nltk.download('punkt')
        if config["vectorize"]["stemming"] == "lancaster":
            stemmer = LancasterStemmer()
        if config["vectorize"]["stemming"] == "porter":
            stemmer = PorterStemmer()
        # TODO does not work?
        config["stop_words"] = (
            [util.stem(stop_word, stemmer) for stop_word in ( 
                config["stop_words"])])
    vectorizer =  TfidfVectorizer(**kwargs)
    x = vectorizer.fit_transform(df[config["payload"]])
    if config["vectorize"]["feature_selection"]["mode"] == "multipleOfLabels":
        topK = len(config["labels"] * config["vectorize"]["feature_selection"]["value"])
    elif config["vectorize"]["feature_selection"]["mode"] == "fractionOfFeatures":
        topK = math.floor(x.shape[1]/config["vectorize"]["feature_selection"]["value"])
    elif config["vectorize"]["feature_selection"]["mode"] == "static":
        topK = config["vectorize"]["feature_selection"]["value"]

    selector = SelectKBest(f_classif, k=min(topK, x.shape[1]))
    # we need the labels, otherwise we cannot guarantee that the selector selects
    # something for every label ?
    selector.fit(x, df.bl)
    return vectorizer, selector, x

def getDisciplineCounts(config, df):
    t = np.zeros((20,20), np.int32)
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
    rows = { i: config["labels"][i] for i in range(0,len(config["labels"])) }
    counts.rename(index = rows, inplace=True)
    return counts

def getSelectedVocabularyAndScores(vocab, selector):
     retval = []
     keys = list(vocab.keys())
     values = list(vocab.values())
     for idx in selector.get_support(indices=True):
         ngram = keys[values.index(idx)]
         score = selector.scores_[idx]
         retval.append([ngram, score])
     return sorted(retval, key=itemgetter(1))
