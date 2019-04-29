import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from mlp import train_ngram_model, ngramVectorize
import util.util as util
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

config = util.loadConfig(args.config)
print("Run model training with configuration {}".format(config["hash"]))

print("Preparing data from directory {}".format(config["rawDataDir"]))

text    = []
labels  = []
for t, l in util.loadSample(config):
   text.extend(t)
   labels.extend(l)
print("Calculating ngrams")
data = ngramVectorize(text, labels, config) 

print("Training the model")
model = train_ngram_model(config)
