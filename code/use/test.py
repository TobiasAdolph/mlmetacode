import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from util.util import loadConfig, loadBinary, loadJsonFromFile
from tensorflow.python.keras import models
import numpy as np
import argparse

parser = argparse.ArgumentParser(
    description='TEST: test a model with a given configuration.'
)
parser.add_argument('--config',
        required    = True,
        help        ="File with the configuration for the training run")
args = parser.parse_args()

config = loadConfig(args.config)
model_file = os.path.join(config["processedDataDir"], "mlp_model.h5")
model = models.load_model(os.path.join(model_file))

#x_val = vectorizer.transform(val_texts)
#x_val = selector.transform(x_val).astype('float32')

tests = [ "mathematics proof theorem lemma number topology deduction",
"particle physics theoretical physics experimental physics atom mass motion star nova",
"chemistry liquid acid protein reaction",
"earth science atmosphere geochemistry geology oceanography hydrology",
"ecology soil environmental sciences",
"biology species population life organism evolution",
"agriculture veterinary crop cattle forest animal slaughterhouse",
"computer science information science library Memory Computation IT programming language code",
"engineering construction electronic structure applied",
"technology nanotechnology biotechnology hardware",
"medical science medicine health science cancer blood pressure leucocytes cardiology fracture insufficience",
"built environment design building bridge architecture designer fabric",
"education pedagogy learn teach children life-long",
"economics economic econometrics",
"commerce management tourism services travel leadership provider",
"social science qualitative politics human society",
"psychology mind cognition think conscious",
"law legal jurisdiction",
"creative arts writing piece creation sculpture music literature",
"language communication culture lingustics tongue socialised gender",
"history archaeology historical",
"philosophy religious studies epistemology ethics god true bad wrong reason theological christian"]

vectorizer = loadBinary(config, "vectorizer.bin")
selector = loadBinary(config, "selector.bin")


anzsrc = loadJsonFromFile(config, "anzsrc.json")

def getCheck(categoryIdx, anzsrcIdx):
    if categoryIdx == i:
        return "PASS"
    else:
        return "FAIL"

i = 0
for test in tests:
    x_test = vectorizer.transform([test])
    x_test = selector.transform(x_test).astype('float32')
    result = model.predict(x_test)[0]
    bestGuesses = result.argsort()[-3:][::-1]
    print("Testing {}\n\t{} ({})".format(test, getCheck(bestGuesses[0], i), anzsrc["{:02}".format(i+1)]))   
    for guess, idx in enumerate(bestGuesses): 
        anzsrcIdx = "{:02}".format(idx + 1)
        print("\t{:02} certainty: {}". format(result[idx], anzsrc[anzsrcIdx]))
    i += 1


#for idx in range(0, len(result)):
#    anzsrc_idx = "{:02}".format(idx + 1)
#    print("{}: {:0.2f}".format(anzsrc[anzsrc_idx], result[idx]))
