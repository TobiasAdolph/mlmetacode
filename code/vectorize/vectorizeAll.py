import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import util.util as util
import json

mode = "test"

config = util.loadConfig("../config/config{}.json".format(mode))

selections = [
        {"mode": "multipleOfLabels", "value": 1000},
        {"mode": "multipleOfLabels", "value": 10000},
        {"mode": "fractionOfFeatures", "value": 100},
        {"mode": "fractionOfFeatures", "value": 10},
        {"mode": "fractionOfFeatures", "value": 1}
]

i = 0
for stemming in ("none", "lancaster", "porter"):
    config["vectorize"]["stemming"] = stemming
    for selection in selections:
        config["vectorize"]["feature_selection"] = selection
        with open("../config/config_{}_{}.json".format(mode, i), "w") as f:
            json.dump(config, f)
        i += 1
