import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import util.util as util
import json
import argparse

def prepare():
    parser = argparse.ArgumentParser(
        description='CLEAN analyze cleaned records'
    )

    parser.add_argument('--config',
            required    = True,
            help        ="File with the configuration for the cleaning run")
    parser.add_argument('--type',
            default    =  "subjectSchemes",
            choices    = ("subjectSchemes", "schemeURIs", "anzsrc2subject"),
            help        ="Display subject schemes")
    parser.add_argument('--anzsrc',
            default    =  "01",
            help        ="Discplay category (only necessary for anzsrc2subject)")
    args = parser.parse_args()

    config = {}
    with open(args.config, "r") as f:
        loadedConfig = json.load(f)
        if "clean" in loadedConfig.keys():
            config = loadedConfig
        else:
            config["clean"] = loadedConfig
    config["clean"]["outputDir"] = os.path.join(
        "../data",
        "processed",
        "clean",
        util.getDictHash(config["clean"]))
    config["base"] = {
        "configDir": "../config/base"
    }

    config["type"] = args.type
    config["anzsrc"] = args.anzsrc
    return config

if __name__ == "__main__":
    config = prepare()
    with open(os.path.join(config["clean"]["outputDir"], config["type"] + ".json"), "r") as f:
        data = json.load(f)
        if config["type"] == "anzsrc2subject":
            anzsrc = util.getAnzsrc(config)
            data = data[anzsrc[config["anzsrc"]]]
    sortedData = sorted(data, key=data.get, reverse=True)
    for sd in sortedData:
        print("{:<{length}}: {}".format(data[sd], sd, length=len(str(data[sortedData[0]]))))
