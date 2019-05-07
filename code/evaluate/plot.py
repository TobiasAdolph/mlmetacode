import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import util.util as util
from tensorflow.python.keras import models
from matplotlib.pyplot import savefig
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sn
import argparse

def plotConfusionMatrix(config, cfm):
    shortAnzsrc = util.getShortAnzsrcAsList(config)
    shortAnzsrc.pop(0)
    df = util.cfm2df(cfm, range(len(shortAnzsrc)))
    df_cfm = pd.DataFrame(
            data=df.values,
            index=shortAnzsrc,
            columns=shortAnzsrc
    )
    plt.figure(figsize = (40,28))
    sn.heatmap(df_cfm, annot=True)
    return plt.plot()

parser = argparse.ArgumentParser(
    description='Plot evaluations for a trained model.'
)

parser.add_argument('--config',
        required    = True,
        help        ="File with the configuration for the training run")


args = parser.parse_args()

config = util.loadConfig(args.config)

model_file = os.path.join(config["processedDataDir"], "train", "mlp_model.h5")
print("Loading model: {}".format(model_file))
model = models.load_model(model_file)

(test_texts, test_labels) = util.loadJsonFromFile(config, "test.json", "train")

cfm = util.getConfusionMatrix(config, model, test_texts, test_labels)
perCfm = cfm/cfm.sum(axis=1, keepdims=True)
plotConfusionMatrix(config, perCfm)
savefig(os.path.join(config["processedDataDir"], "evaluate", "cfm.png"))
