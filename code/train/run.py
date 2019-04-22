import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from mlp import train_ngram_model
from util.util import loadConfig
import argparse

parser = argparse.ArgumentParser(
    description='TRAIN: Run a training with a given configuration.'
)


parser.add_argument('--config',
        required    = True,
        help        ="File with the configuration for the training run")
args = parser.parse_args()

if not os.path.isfile(args.config):
    print("{} is not a path to a file".format(args.config))

config = loadConfig(args.config)

# Run ngram vectorize over ALL data and store vectorizer and selector!

model = train_ngram_model(config)
#model = models.load_model('dmaxAll_mlp.model.h5')
#
#((train_texts, train_labels), (test_texts, test_labels)) = load_sample("../data/dmin", mode="all")
#x_train, x_test = ngram_vectorize(
#        train_texts, train_labels, test_texts)
#results = model.evaluate(x_test, test_labels)
#pprint.pprint(results)
#
#predictions = []
#for x in model.predict(x_test):
#    predictions.append(np.argmax(x)) 
#cfm = confusion_matrix(
#        test_labels,
#        predictions)
#import seaborn as sn
#import pandas as pd
#import matplotlib.pyplot as plt
#df_cm = pd.DataFrame(cm2df(cfm, range(22)), range(22), range(22))
#plt.figure(figsize = (10,7))
#sn.heatmap(df_cm, annot=True) 
