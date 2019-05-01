import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from util.util import loadConfig, loadBinary, loadJsonFromFile
from tensorflow.python.keras import models
import argparse
import json

parser = argparse.ArgumentParser(
    description='Classificator of the Discipline of Research'
)
parser.add_argument('--config',
        required    = True,
        help        ="File with the configuration")
parser.add_argument('--metadata',
        required    = True,
        help        ="File with the metadata to-be-classified")
args = parser.parse_args()

config = loadConfig(args.config)
model_file = os.path.join(config["processedDataDir"], "train", "mlp_model.h5")
model = models.load_model(model_file)
vectorizer = loadBinary(config, "vectorizer.bin", "train")
selector = loadBinary(config, "selector.bin", "train")
anzsrc = loadJsonFromFile(config, "anzsrc.json")

with open(args.metadata, "r") as f:
    metadata = json.load(f)


payload = [] 
for field in config["dmode"].split("_"):
    payload.append(metadata[field + "s"][0][field])

text = " ".join(payload)
x = vectorizer.transform([text])
x = selector.transform(x).astype('float64')

result = model.predict(x)[0]
for dId in result.argsort()[::-1]:
    anzsrcName = anzsrc["{:02}".format(dId + 1)]
    print("{:20.16F} percent probability: {}".format(result[dId]*100, anzsrcName))

