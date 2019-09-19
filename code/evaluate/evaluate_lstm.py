import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import pandas as pd
import util.util as util
import vectorize.vectorizeHelpers as vectorizeHelpers
import numpy as np
from sklearn.model_selection import train_test_split
import scipy.sparse
import keras
from keras import backend as K
from keras.models import Model
from keras.layers import Dense, Dropout, LSTM, Bidirectional, Input
from keras.layers.embeddings import Embedding
from keras.callbacks import EarlyStopping
from keras.preprocessing.sequence import pad_sequences
from sklearn.metrics import precision_score, recall_score, fbeta_score, precision_recall_fscore_support
from random import randint
from keras import Tokenizer
from gensim.models import KeyedVectors
import json


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


def lstm_embedding(sequences):
    tokenizer = Tokenizer(lower=True)
    tokenizer.fit_on_texts(sequences)
    word2vec_path = "/home/debian/ml/data/embedding/GoogleNews-vectors-negative300.bin"
    model = KeyedVectors.load_word2vec_format(word2vec_path, binary=True)
    word_index = tokenizer.word_index
    embedding_matrix = np.zeros((len(word_index + 1), 300))
    word_vectors = model.wv
    for word, i in word_index.items():
        try:
            embedding_vector = word_vectors[word]
            embedding_matrix[i] = embedding_vector
        except:
            pass
    return tokenizer, embedding_matrix, word_index


def lstm_model(x_train, x_val, y_train, y_val, word_index, input_length, class_weight, embedding_matrix, callbacks):
    #TODO check hyperparams for LSTM
    lstm_size = 512
    droput = 0.2
    recurrent_dropout = 0.2
    learning_rate=0.001
    optimizer = keras.optimizers.Adam(lr=learning_rate)
    loss ="binary_crossentropy"
    epochs = 100
    batch_size = 100

    inputs = Input(shape=(input_length, ))
    embedding = Embedding(len(word_index) + 1, output_dim=300, weights=[embedding_matrix],
                          nput_length=input_length, trainable=False)(input)
    lstm = Bidirectional(LSTM(lstm_size, dropout = droput, recurrent_dropout=recurrent_dropout), merge_mode='concat')(embedding)
    output = Dense(class_weight, activation="sigmoid")(lstm)
    final_model = Model(inputs=inputs, outputs = output)
    final_model.compile(loss=loss, optimizer=optimizer, metrics=[macro_recall, macro_precision, fone_loss])

    history_output = final_model.fit(x_train, y_train, epochs=epochs, callbacks=callbacks, validation_data=(x_val, y_val),
        verbose=2, batch_size=batch_size, class_weight=class_weight)
    return final_model, history_output


if __name__ == "__main__":
    config = prepare()
    df = pd.read_csv(config["src"], index_col=0)
    df = df[df.wc >= config["wc"]]
    df = df[df.nol < 8]
    df["payloadFinal"] = df.payload
    df.labelsI = df.labels.apply(lambda x: util.int2bv(x, 21)[1:]).tolist()
    config["logger"].info("Vectorizing {}".format(config["src"]))
    (vectorizer, selector, x) = vectorizeHelpers.getVectorizerAndSelector(config, df)
    config["seed"] = randint(0, 2 ** 32 - 1)
    xSelected = selector.transform(x).astype(np.float64)

    config["logger"].info("Splitting with seed {}".format(config["seed"]))

    x_train_val, x_test, y_train_val, y_test, bl_train_val, bl_test = (train_test_split(xSelected, df.labelsI.tolist(),
            df.bl, test_size=0.1, shuffle=True, stratify=df.bl, random_state=config["seed"]))

    x_train, x_val, y_train, y_val = (train_test_split(x_train_val, y_train_val, test_size=0.1, shuffle=True,
            stratify=bl_train_val, random_state=config["seed"]))

    numbers = np.sum(y_train, axis = 0)
    class_weight = np.apply_along_axis(lambda x: 1/(x/max(numbers)), 0, numbers).tolist()

    y_train = scipy.sparse.csc_matrix(y_train)
    y_val = scipy.sparse.csc_matrix(y_val)
    y_test = scipy.sparse.csc_matrix(y_test)

    tokenizer, embedding_matrix, word_index = lstm_embedding(df["payloadFinal"])
    #TODO specify max length
    maxlen = 60
    sequences_train = tokenizer.texts_to_sequences(x_train)
    sequences_validation = tokenizer.texts_to_sequences(x_val)
    sequences_test = tokenizer.texts_to_sequences(x_test)
    data_train = pad_sequences(sequences_train, maxlen=maxlen)
    data_validation = pad_sequences(sequences_validation, maxlen=maxlen)
    data_test = pad_sequences(sequences_test, maxlen=maxlen)

    callbacks = [EarlyStopping(monitor='val_loss', patience=5, verbose=1, restore_best_weights=True)]
    model, history = lstm_model(data_train, data_validation, y_train, y_val, word_index, maxlen, class_weight,
                    embedding_matrix, callbacks)

    model.evaluate(data_test, y_test, batch_size=2 ** 13)

    m_spec = {}
    m_spec["history"] = history.history

    y_pred = prob2onehot(model.predict(x_test))

    m_spec["evaluation"] = {
        "precision": precision_recall_fscore_support(y_test, y_pred)[0].tolist(),
        "recall": precision_recall_fscore_support(y_test, y_pred)[1].tolist(),
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