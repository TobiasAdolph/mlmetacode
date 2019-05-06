
from tensorflow.python.keras import models
from tensorflow.python.keras.layers import Dense
from tensorflow.python.keras.layers import Dropout
import numpy as np
import os, sys
import pandas as pd
import tensorflow as tf

import util.util as util

def _get_last_layer_units_and_activation(num_classes):
    """Gets the # units and activation function for the last network layer.

    # Arguments
        num_classes: int, number of classes.

    # Returns
        units, activation values.

    # References
        directly taken from
        https://developers.google.com/machine-learning/guides/text-classification/step-4
    """
    if num_classes == 2:
        activation = 'sigmoid'
        units = 1
    else:
        activation = 'softmax'
        units = num_classes
    return units, activation

def mlp_model(layers, units, dropout_rate, input_shape, num_classes):
    """Creates an instance of a multi-layer perceptron model.

    # Arguments
        layers: int, number of `Dense` layers in the model.
        units: int, output dimension of the layers.
        dropout_rate: float, percentage of input to drop at Dropout layers.
        input_shape: tuple, shape of input to the model.
        num_classes: int, number of output classes.

    # Returns
        An MLP model instance.
    # References
        Directly taken from
        https://developers.google.com/machine-learning/guides/text-classification/step-4
    """
    op_units, op_activation = _get_last_layer_units_and_activation(num_classes)
    model = models.Sequential()
    model.add(Dropout(rate=dropout_rate, input_shape=input_shape))

    for _ in range(layers-1):
        model.add(Dense(units=units, activation='relu'))
        model.add(Dropout(rate=dropout_rate))

    model.add(Dense(units=op_units, activation=op_activation))
    return model

def get_num_classes(labels):
    """Gets the total number of classes.
    # Arguments
        labels: list, label values.
            There should be at lease one sample for values in the
            range (0, num_classes -1)
    # Returns
        int, total number of classes.
    # Raises
        ValueError: if any label value in the range(0, num_classes - 1)
            is missing or if number of classes is <= 1.
    # References
        directly taken from
        https://github.com/google/eng-edu/blob/master/ml/guides/text_classification/explore_data.py
    """
    num_classes = max(labels) + 1
    missing_classes = [i for i in range(num_classes) if i not in labels]
    if len(missing_classes):
        raise ValueError('Missing samples with label value(s) '
                         '{missing_classes}. Please make sure you have '
                         'at least one sample for every label value '
                         'in the range(0, {max_class})'.format(
                            missing_classes=missing_classes,
                            max_class=num_classes - 1))

    if num_classes <= 1:
        raise ValueError('Invalid number of labels: {num_classes}.'
                         'Please make sure there are at least two classes '
                         'of samples'.format(num_classes=num_classes))
    return num_classes

def train_ngram_model(config):
    """Trains n-gram model on the given dataset.

    # Arguments
        config: dict, config hash

    # Raises
        ValueError: If validation data has label values which were not seen
            in the training data.

    # References
        directly taken from
        https://developers.google.com/machine-learning/guides/text-classification/step-4
    """
    # Get the data.

    (train_texts, train_labels), (val_texts, val_labels), (test_texts, test_labels) = (
            util.loadSample(config))


    # Verify that validation labels are in the same range as training labels.
    num_classes = get_num_classes(train_labels)
    unexpected_labels = [v for v in val_labels if v not in range(num_classes)]
    if len(unexpected_labels):
        raise ValueError('Unexpected label values found in the validation set:'
                         ' {unexpected_labels}. Please make sure that the '
                         'labels in the validation set are in the same range '
                         'as training labels.'.format(
                             unexpected_labels=unexpected_labels))


    # Vectorize texts.
    x_train = util.ngramVectorize(train_texts, train_labels, config)
    x_val = util.ngramVectorize(val_texts, val_labels, config, False)

    print("after vectorizing")
    # Create model instance.
    model = mlp_model(layers=config["layers"],
                                  units=config["units"],
                                  dropout_rate=config["dropoutRate"],
                                  input_shape=x_train.shape[1:],
                                  num_classes=num_classes)
    print("after model")

    # Compile model with learning parameters.
    if num_classes == 2:
        loss = 'binary_crossentropy'
    else:
        loss = 'sparse_categorical_crossentropy'

    optimizer = tf.keras.optimizers.Adam(lr=config["learningRate"])
    model.compile(optimizer=optimizer, loss=loss, metrics=['acc'])

    print("after model compilation")
    # Create callback for early stopping on validation loss. If the loss does
    # not decrease in two consecutive tries, stop training.
    callbacks = [tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=2)]

    # Train and validate model.
    history = model.fit(
            x_train,
            train_labels,
            epochs=config["epochs"],
            callbacks=callbacks,
            validation_data=(x_val, val_labels),
            verbose=2,  # Logs once per epoch.
            batch_size=config["batchSize"])

    # Print results.
    history = history.history
    print('Validation accuracy: {acc}, loss: {loss}'.format(
            acc=history['val_acc'][-1], loss=history['val_loss'][-1]))

    # Save model
    model_file = os.path.join(config["processedDataDir"], "train", "mlp_model.h5")
    model.save(model_file)
    return model
