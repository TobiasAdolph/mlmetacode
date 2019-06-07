import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import util.util as util
import json
import argparse
import pandas as pd

def prepare():
    parser = argparse.ArgumentParser(
        description='CLEAN analyze cleaned records'
    )

    parser.add_argument('--config',
            required    = True,
            help        ="File with the configuration for the cleaning run")
    parser.add_argument('--type',
            default    =  "subjectSchemes",
            choices    = ("subjectSchemes", "schemeURIs", "scheme2label"),
            help        ="Display subject schemes")
    parser.add_argument('--label',
            default    =  "1",
            help        ="Display scheme hits for this label (scheme2label)")
    parser.add_argument('--scheme',
            default    =  "all",
            help        ="Display scheme hits for this scheme (scheme2label)")

    args = parser.parse_args()

    config = util.loadConfig(args.config)
    config["type"] = args.type
    config["label"] = args.label
    config["scheme"] = args.scheme
    return config

def printScheme2Labels(stat, scheme, label):
    selection = stat[(stat[label]) & (stat[scheme] != "") & (stat["useable"])]
    print(selection.groupby(scheme)[scheme].count().sort_values(ascending=False))

if __name__ == "__main__":
    config = prepare()
    if config["type"] == "scheme2label":
        store = pd.HDFStore(os.path.join(config["clean"]["outputDir"], "stat.h5"))
        stat = store["statistics"]
        if config["scheme"] == "all":
            formatString = 20 *"-" + " {} " + 20 * "-"
            for scheme in config["clean"]["schemes"]:
                print(formatString.format(scheme))
                printScheme2Labels(stat, scheme, config["label"])
        else:
            printScheme2Labels(stat, config["scheme"], config["label"])
        label = config["label"]
        scheme = config["scheme"]
    else:
        with open(os.path.join(config["clean"]["outputDir"], config["type"] + ".json"), "r") as f:
            data = json.load(f)
        sortedData = sorted(data, key=data.get, reverse=True)
        for sd in sortedData:
            print("{:<{length}}: {}".format(data[sd], sd, length=len(str(data[sortedData[0]]))))
