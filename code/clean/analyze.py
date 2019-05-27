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
            help        ="Display subject schemes")
    args = parser.parse_args()

    config = util.loadConfig(args.config)
    config["type"] = args.type
    return config

if __name__ == "__main__":
    config = prepare()
    with open(os.path.join(config["clean"]["outputDir"], config["type"] + ".json"), "r") as f:
        data = json.load(f)
        sortedData = sorted(data, key=data.get, reverse=True)
        for sd in sortedData:
            print("{:<{length}}: {}".format(data[sd], sd, length=len(str(data[sortedData[0]]))))
