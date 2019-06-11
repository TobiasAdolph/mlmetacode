import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from mlp import train_ngram_model
import util.util as util
import argparse
import scipy.sparse
import pandas as pd

def prepare():
    parser = argparse.ArgumentParser(
        description='TRAIN: Run a training with a given configuration.'
    )

    parser.add_argument('--config',
            required    = True,
            help        ="File with the configuration for the training run")
    args = parser.parse_args()
    config = util.loadConfig(args.config)
    config["logger"] = util.setupLogging(config, "train")
    config["labels"] = util.getLabels(config)
    config["srcDir"] = os.path.join(
        config["vectorize"]["baseDir"],
        config["train"]["vectorizeHash"]
    )
    return config

if __name__ == "__main__":
    config = prepare()
    print("Run model training with configuration {}".format(config["train"]["hash"]))
    x_train = scipy.sparse.load_npz(os.path.join(config["srcDir"], "train_data.npz"))
    store = pd.HDFStore(os.path.join(config["srcDir"], "train_labels.h5"))
    y_train = store["labels"]
    store.close()
    x_val = scipy.sparse.load_npz(os.path.join(config["srcDir"], "val_data.npz"))
    store = pd.HDFStore(os.path.join(config["srcDir"], "val_labels.h5"))
    y_val = store["labels"]
    store.close()
    model = train_ngram_model(config, x_train, y_train, x_val, y_val) 
    model_file = os.path.join(
        config["train"]["outputDir"],
        config["train"]["hash"] + ".model"
    )
    model.save(model_file)
