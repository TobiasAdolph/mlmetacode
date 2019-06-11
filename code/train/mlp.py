import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import util.util as util
from tensorflow.python.keras import models
from tensorflow.python.keras.layers import Dense
from tensorflow.python.keras.layers import Dropout
import numpy as np
import pandas as pd
import tensorflow as tf
import scipy.sparse

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

def train_ngram_model(config, x_train, y_train, x_val, y_val):
    """Trains n-gram model on the given dataset.

    # Arguments
        config: dict, config hash
        dataFile: path to file containing text and labels

    # Raises
        ValueError: If validation data has label values which were not seen
            in the training data.

    # References
        directly taken from
        https://developers.google.com/machine-learning/guides/text-classification/step-4
    """
    config["logger"].info("Testing data and labels have been saved")

    # Create model instance.
    model = mlp_model(layers=config["train"]["mlpConfig"]["layers"],
                                  units=config["train"]["mlpConfig"]["units"],
                                  dropout_rate=config["train"]["mlpConfig"]["dropoutRate"],
                                  input_shape=x_train.shape[1:],
                                  num_classes=len(config["labels"]))

    # Compile model with learning parameters.
    loss = 'sparse_categorical_crossentropy'

    optimizer = tf.keras.optimizers.Adam(lr=config["train"]["mlpConfig"]["learningRate"])
    model.compile(optimizer=optimizer, loss=loss, metrics=['acc'])

    config["logger"].info("Model compiled")
    # Create callback for early stopping on validation loss. If the loss does
    # not decrease in two consecutive tries, stop training.
    callbacks = [tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=2)]

    # Train and validate model.
    history = model.fit(
            x_train,
            y_train,
            epochs=config["train"]["mlpConfig"]["epochs"],
            callbacks=callbacks,
            validation_data=(x_val, y_val),
            verbose=2,  # Logs once per epoch.
            batch_size=config["train"]["mlpConfig"]["batchSize"])

    # Print results.
    history = history.history
    config["logger"].info('Validation accuracy: {acc}, loss: {loss}'.format(
            acc=history['val_acc'][-1], loss=history['val_loss'][-1]))

    # Save model
    return model
