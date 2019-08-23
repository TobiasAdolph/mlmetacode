import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import util.util as util
import json

mode = ""

config = util.loadConfig("../config/config{}.json".format(mode))

selections = [
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 1000},
            "stemming": "none"
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 2500},
            "stemming": "none"
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 5000},
            "stemming": "none",
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 1000},
            "stemming": "lancaster"
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 2500},
            "stemming": "lancaster"
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 5000},
            "stemming": "lancaster"
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 1000},
            "stemming": "porter"
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 2500},
            "stemming": "porter"
        },
        { 
            "feature_selection": {"mode": "multipleOfLabels", "value": 5000},
            "stemming": "porter"
        }
]

for selection in selections:
    name_parts = []
    for key, value in selection.items():
        config["vectorize"][key] = value
        if type(value) is dict:
            name_parts.append(str(value["value"]))
        else:
            name_parts.append(str(value))
    print("../config/config{}_{}.json".format(mode, "_".join(name_parts)))
    with open("../config/config{}_{}.json".format(mode, "_".join(name_parts)), "w") as f:
        json.dump(config, f)
