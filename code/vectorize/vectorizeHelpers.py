import numpy as np
import pandas as pd
import json
import os
import re
import pickle
import math

import scipy.sparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_classif
from gensim.models import KeyedVectors
from keras import Tokenizer

from nltk.stem.lancaster import LancasterStemmer
from nltk.stem.porter import PorterStemmer

def vectorizeEmbeddings(config, df):
    """ Vectorize the payload in df as embeddings

    # Arguments:
        config:  a dictionary with the configuration 
        df: a pandas dataFrame with the data (key: payload)

    # Returns
        The embeddings as a sparse matrix

    # See
        vectorizeBagOfWords
    """
    #sequences = df["payloadFinal"]
    #tokenizer = Tokenizer(lower=True)
    #tokenizer.fit_on_texts(sequences)
    #word_index = tokenizer.word_index
    #print('Found %s unique tokens.' % len(word_index))
    #word2vec_path = "/home/debian/ml/data/embedding/GoogleNews-vectors-negative300.bin"
    #model = KeyedVectors.load_word2vec_format(word2vec_path, binary=True)
    #embedding_matrix = np.zeros((len(word_index + 1), 300))
    #word_vectors = model.wv
    #for word, i in word_index.items():
    #    try:
    #        embedding_vector=word_vectors[word]
    #        embedding_matrix[i] = embedding_vector
    #    except:
    #        pass
    #return embedding_matrix

def vectorizeBagOfWords(config, df):
    """ Vectorize the payload in df as bag of words 

    # Arguments:
        config:  a dictionary with the configuration 
        df: a pandas dataFrame with the data (key: payload)

    # Returns
        The bag of words as a sparse matrix
    # See
        vectorizeEmbeddings
    """
    vectorizer, selector, x = getVectorizerAndSelector(config, df)
    return selector.transform(x).astype(np.float64)

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
    return (
        vectorizer,
        selector,
        x
    )

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
         if len(retval) == 0:
             retval.append([ngram, score])
             continue
         for i in range(0,len(retval)+1):
             if i >= len(retval):
                 retval.append([ngram, score])
                 break
             if retval[i][1] < score:
                 retval.insert(i, [ngram, score])
                 break
     return retval
