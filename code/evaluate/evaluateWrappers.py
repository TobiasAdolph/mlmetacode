import keras
from keras import models
from keras.layers import Dense, Dropout, LSTM, Bidirectional, Input
from keras.layers.embeddings import Embedding
from keras import backend as K
from sklearn.metrics import precision_score, recall_score, fbeta_score, precision_recall_fscore_support
from keras.layers.embeddings import Embedding
import numpy as np

def micro_recall(y_true, y_pred):
        """Recall metric.

        Only computes a batch-wise average of recall.

        Computes the recall, a metric for multi-label classification of
        how many relevant items are selected.
        """
        true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
        possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
        recall = true_positives / (possible_positives + K.epsilon())
        return recall

def micro_precision(y_true, y_pred):
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
    precision = micro_precision(y_true, y_pred)
    recall = micro_recall(y_true, y_pred)
    return 1 - (2*precision*recall)/(precision+recall)

def prob2onehot(y):
    y[y >= 0.5] = 1
    y[y <  0.5] = 0
    return y

class TFClassifier(object):
    def predict(self, x):
        return prob2onehot(self.model.predict(x, batch_size=512, verbose=1))

    def getOptimizer(self):
        if self.optimizer == "adam":
            return keras.optimizers.Adam(lr=self.learning_rate)

    def getCallbacks(self):
        return [ 
            keras.callbacks.EarlyStopping(
                monitor=self.early_stopping_metric,
                patience=self.early_stopping_patience,
                min_delta=self.early_stopping_delta
            )
        ]

    def to_json(self):
        return self.model.to_json()

    def save_weights(self, path):
        return self.model.save_weights(path)

class MLPClassifier(TFClassifier):
    def addHiddenLayer(self, units=100, activation="relu", rate=0.2):
        self.model.add(Dense(units=units, activation=activation))
        self.model.add(Dropout(rate=rate))

    def addInitLayer(self, x_train, rate):
        self.model = models.Sequential()
        self.model.add(Dropout(rate=rate, input_shape=(x_train.shape[1],)))

    def addOutputLayer(self, y_train, activation="sigmoid"):
        self.model.add(Dense(units=y_train.shape[1], activation=activation))

    # TODO seed, multiprocessing 
    def fit(self, x_train, y_train, x_val, y_val):
        np.random.seed(self.random_state)
        self.addInitLayer(x_train, self.init_rate)
        for idx,ly in enumerate(self.hidden_layer):
            self.addHiddenLayer(units=ly, activation=self.activation[idx], rate=self.rate[idx])
        model = self.addOutputLayer(y_train)
        self.model.compile(
                optimizer=self.getOptimizer(),
                loss=self.loss,
                metrics=[fone_loss, micro_recall, micro_precision]
        )
        return self.model.fit(
            x_train,
            y_train,
            epochs=self.epochs,
            callbacks=self.getCallbacks(),
            validation_data=(x_val, y_val),
            verbose=2,
            batch_size=self.batch_size,
            class_weight=self.class_weight
        )

class LSTMClassifier(TFClassifier):
    def __init__(self, tokenizer, embedding_matrix, maxlen):
        self.tokenizer = tokenizer
        self.embedding_matrix = embedding_matrix
        self.maxlen = maxlen

    def fit(self, x_train, y_train, x_val, y_val):
        np.random.seed(self.random_state)
        inputs = Input(shape=(self.maxlen,))
        print(len(self.tokenizer.word_index))
        print(self.embedding_matrix.shape)
        embedding = Embedding(
            len(self.tokenizer.word_index) + 1,
            output_dim=self.output_dim,
            weights=[self.embedding_matrix],
            input_length=self.maxlen,
            trainable=self.trainable)(inputs)
        if self.bidirectional:
            lstm = Bidirectional(
                LSTM(
                    self.lstm_size,
                    dropout=self.dropout,
                    recurrent_dropout=self.recurrent_dropout
                ),
                merge_mode=self.merge_mode)(embedding)
        else:
            lstm = LSTM(
                    self.lstm_size,
                    dropout=self.dropout,
                    recurrent_dropout=self.recurrent_dropout
                )(embedding)
        outputs = Dense(units=y_train.shape[1], activation="sigmoid")(lstm)
        self.model = models.Model(inputs=inputs,outputs=outputs)
        self.model.compile(
                loss=self.loss,
                optimizer = self.getOptimizer(),
                metrics=[fone_loss, micro_recall, micro_precision]
        )
        return self.model.fit(
            x_train,
            y_train,
            epochs=self.epochs,
            callbacks=self.getCallbacks(),
            validation_data=(x_val, y_val),
            verbose=2,
            batch_size=self.batch_size,
            class_weight=self.class_weight
        )
