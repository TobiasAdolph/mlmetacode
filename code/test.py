from util import loadConfig, loadBinary, loadJsonFromFile
from tensorflow.python.keras import models
import numpy as np
import os

config = loadConfig()
model_file = os.path.join(config["dataDir"],
            "{}_{}_mlp_model.h5".format(config["dtype"], config["dmode"])
)
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
    categoryIdx = np.argmax(result)
    anzsrcIdx = "{:02}".format(categoryIdx + 1)
    print("{}: {} is {} with {:02} certainty".format(getCheck(categoryIdx, i), test, anzsrc[anzsrcIdx], result[categoryIdx])) 
    i += 1


#for idx in range(0, len(result)):
#    anzsrc_idx = "{:02}".format(idx + 1)
#    print("{}: {:0.2f}".format(anzsrc[anzsrc_idx], result[idx]))
