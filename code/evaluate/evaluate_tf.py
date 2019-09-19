import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import pandas as pd
import util.util as util
import vectorize.vectorizeHelpers as vectorizeHelpers
import numpy as np
from sklearn.model_selection import train_test_split
import scipy.sparse
import keras
from keras import models
from keras.layers import Dense
from keras.layers import Dropout
from keras import backend as K
from sklearn.metrics import precision_score, recall_score, fbeta_score, precision_recall_fscore_support
import json
from random import randint
import argparse

def addHiddenLayer(model, m_spec, units=100, activation="relu", rate=0.2):
    model.add(Dense(units=units, activation=activation))
    model.add(Dropout(rate=rate))
    m_spec["layers"].append(
            {
                "units": units,
                "activation": activation,
                "rate": rate
            }
    )
    return (model, m_spec)

def addInitLayer(model, x_train, rate):
    model.add(Dropout(rate=rate, input_shape=(x_train.shape[1],)))
    m_spec = {"layers":  [ {"rate": rate, "input_shape": x_train.shape[1] } ] }
    return (model, m_spec)

def addOutputLayer(model, m_spec, y_train, activation="sigmoid"):
    model.add(Dense(units=y_train.shape[1], activation=activation))
    m_spec["layers"].append({"units": y_train.shape[1], "activation": activation })
    return (model, m_spec)

def getOptimizer(m_spec, lr=0.001):
    m_spec["optimizer"] = { "oType": "adam", "lr": lr }
    return (keras.optimizers.Adam(lr=lr), m_spec)

def prec_micro(y_true, y_pred):
    return precision_score(y_true, y_pred, average="micro")

def prec_macro(y_true, y_pred):
    return precision_score(y_true, y_pred, average="macro")

def rec_micro(y_true, y_pred):
    return recall_score(y_true, y_pred, average="micro")

def rec_macro(y_true, y_pred):
    return recall_score(y_true, y_pred, average="macro")

def macro_recall(y_true, y_pred):
        """Recall metric.

        Only computes a batch-wise average of recall.

        Computes the recall, a metric for multi-label classification of
        how many relevant items are selected.
        """
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
        recall = true_positives / (possible_positives + K.epsilon())
        return recall

def macro_precision(y_true, y_pred):
        """Precision metric.

        Only computes a batch-wise average of precision.

        Computes the precision, a metric for multi-label classification of
        how many selected items are relevant.
        """
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
        precision = true_positives / (predicted_positives + K.epsilon())
        return precision

def fone_loss(y_true, y_pred):
    precision = macro_precision(y_true, y_pred)
    recall = macro_recall(y_true, y_pred)
    return 1 - (2*precision*recall)/(precision+recall)

def prob2onehot(y):
    y[y >= 0.5] = 1
    y[y <  0.5] = 0
    return y

def prepare():
    parser = argparse.ArgumentParser(
        description='EVALUATE neural networks'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'evaluate'")
    parser.add_argument('--wc',
            default = 50,
            help = "Minimum numbers of words per sample")
    parser.add_argument('--fs',
            default = 1000,
            help = "Number of features per label to be selected")
    parser.add_argument('--ly',
            required = True,
            nargs="+",
            type=int,
            help = "layers given as whitespace separated number of units")
    parser.add_argument('--batch_size',
            default = 2**10,
            help = "Number of features per label to be selected")
    parser.add_argument('--epoch',
            default = 1000,
            help = "Number of features per label to be selected")
    args = parser.parse_args()
    config = util.loadConfig(args.config)
    print("Starting with config {}\n\ttail -f {}".format(
        config["evaluate"]["hash"],
        config["evaluate"]["logFile"]
    ))
    config["logger"] = util.setupLogging(config, "evaluate")
    config["src"] = os.path.join(config["clean"]["baseDir"],
                 config["vectorize"]["cleanHash"],
                "useable.csv"
    )
    config["wc"] = int(args.wc)
    config["vectorize"]["feature_selection"]["value"] = int(args.fs)
    config["ly"] = []
    for ly in args.ly:
        config["ly"].append(int(ly))
    config["batch_size"] = int(args.batch_size)
    config["epoch"] = args.epoch
    config["labels"] = util.getLabels(config)[1:]
    config["stop_words"] = util.getStopWords(config)
    return config

if __name__ == "__main__":
    config = prepare()
    df = pd.read_csv(config["src"], index_col=0)
    df = df[df.wc >= config["wc"]]
    df = df[df.nol < 8]
    df["payloadFinal"] = df.payload
    df.labelsI = df.labels.apply(lambda x: util.int2bv(x, 21)[1:]).tolist()
    config["logger"].info("Vectorizing {}".format(config["src"]))
    (vectorizer, selector, x) = vectorizeHelpers.getVectorizerAndSelector(config, df)
    config["seed"] = randint(0,2**32-1) 
#    with open(os.path.join(config["vectorize"]["outputDir"], str(config["seed"]) + "_vocab_scores.json"), "w") as f:
#        json.dump(vectorizeHelpers.getSelectedVocabularyAndScores(vectorizer.vocabulary_, selector),f)

    xSelected = selector.transform(x).astype(np.float64)

    config["logger"].info("Splitting with seed {}".format(config["seed"]))
  
    x_train_val, x_test, y_train_val, y_test, bl_train_val, bl_test = (
        train_test_split(
            xSelected,
            df.labelsI.tolist(),
            df.bl,
            test_size=0.1,
            shuffle=True,
            stratify=df.bl,
            random_state = config["seed"]
        )
    )
    x_train, x_val, y_train, y_val = (
        train_test_split(
            x_train_val,
            y_train_val,
            test_size=0.1,
            shuffle=True,
            stratify=bl_train_val,
            random_state = config["seed"]
        )
    )

    numbers = np.sum(y_train, axis = 0)
    class_weight = np.apply_along_axis(lambda x: 1/(x/max(numbers)), 0, numbers).tolist()
    y_train_val = scipy.sparse.csc_matrix(y_train_val)
    y_train = scipy.sparse.csc_matrix(y_train)
    y_val = scipy.sparse.csc_matrix(y_val)
    y_test = scipy.sparse.csc_matrix(y_test)



    model = models.Sequential()

    # TODO: specifiy values via params
    model, m_spec = (addInitLayer(model, x_train, 0.1))
    for ly in config["ly"]:
        model, m_spec = (addHiddenLayer(model, m_spec, units=ly))
    model, m_spec = (addOutputLayer(model, m_spec, y_train))
    
    m_spec["dataHash"] = config["vectorize"]["cleanHash"]
    m_spec["loss"] = "binary_crossentropy"
    optimizer, m_spec =  (getOptimizer(m_spec))
    model.compile(
        optimizer=optimizer,
        loss=m_spec["loss"],
        metrics=[macro_recall, macro_precision, fone_loss]
    )
    callbacks = [keras.callbacks.EarlyStopping(monitor='val_fone_loss', patience=1)]
    m_spec["fit"] = {
        "epochs": config["epoch"],
        "batch_size": config["batch_size"],
        "class_weight": class_weight
    }

    # Put seed here to be hashed for the name
    m_spec["seed"] = config["seed"]
    config["target"] = ("wc-" + str(df.wc.min()) +
        "_fs-" + str(config["vectorize"]["feature_selection"]["value"]) +
        "_" + util.getDictHash(m_spec)[0:10])

    for idx, ly in reversed(list(enumerate(m_spec["layers"]))):
        config["target"] = "l{}-{}_".format(idx, ly.get("units", "fs")) + config["target"] 
    config["target"] = os.path.join(config["base"]["outputDir"], config["target"])
    history = model.fit(
        x_train,
        y_train,
        epochs=m_spec["fit"]["epochs"],
        callbacks=callbacks,
        validation_data=(x_val, y_val),
        verbose=2,
        batch_size=m_spec["fit"]["batch_size"],
        class_weight=m_spec["fit"]["class_weight"]
    )
    
    callbacks = [keras.callbacks.EarlyStopping(monitor='fone_loss', patience=1, min_delta=0.01)]
    history = model.fit(
        x_train_val,
        y_train_val,
        epochs=5,
        callbacks=callbacks,
        verbose=2,
        batch_size=m_spec["fit"]["batch_size"],
        class_weight=m_spec["fit"]["class_weight"]
    )

    model.evaluate(x_test,y_test, batch_size=2**13)
    m_spec["history"] = history.history

    y_pred = prob2onehot(model.predict(x_test))

    m_spec["evaluation"] = {
        "precision" :  precision_recall_fscore_support(y_test, y_pred)[0].tolist(),
        "recall": precision_recall_fscore_support(y_test, y_pred)[1].tolist() ,
        "fhalf": precision_recall_fscore_support(y_test, y_pred, beta=0.5)[2].tolist(),
        "fone": precision_recall_fscore_support(y_test, y_pred, beta=1)[2].tolist(),
        "ftwo": precision_recall_fscore_support(y_test, y_pred, beta=2)[2].tolist(),
        "fhalf_micro": fbeta_score(y_test, y_pred, average="micro", beta=0.5),
        "fhalf_macro": fbeta_score(y_test, y_pred, average="macro", beta=0.5),
        "fone_micro": fbeta_score(y_test, y_pred, average="micro", beta=1),
        "fone_macro": fbeta_score(y_test, y_pred, average="macro", beta=1),
        "ftwo_micro": fbeta_score(y_test, y_pred, average="micro", beta=2),
        "ftwo_macro": fbeta_score(y_test, y_pred, average="macro", beta=2)
    }

    with open("test.json", "r") as f:
        test_data = json.load(f)
        x_test_data = selector.transform(vectorizer.transform(test_data).astype(np.float64))
        y_test_data = prob2onehot(model.predict(x_test_data))
        m_spec["evaluation"]["wiki_diag"] = sum(np.diag(y_test_data))/y_test.shape[1]
        m_spec["evaluation"]["wiki_sum"] = sum(sum(y_test_data))/y_test.shape[1]

    with open(config["target"] + ".json", "w") as f:
        json.dump(m_spec, f)
