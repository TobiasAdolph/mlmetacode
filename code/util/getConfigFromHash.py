import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import json
from util import loadConfig
import  pprint

def prepare():
    parser = argparse.ArgumentParser(
        description='Print a config to a given hash and step'
    )
    parser.add_argument('--config',
            required = True,
            help = "Main configuration file")
    parser.add_argument('--hash',
            required = True,
            help = "Hash to be checked")
    parser.add_argument('--step',
            required = True,
            help = "Step to be checked")


    args = parser.parse_args()
    config = loadConfig(args.config)
    config["cHash"] = args.hash
    config["step"] = args.step
    return config

if __name__ == "__main__":
    config = prepare()
    targetConfigFile = os.path.join(
        config[config["step"]]["configDir"],
        config["cHash"] + ".json")
    if not os.path.exists(targetConfigFile):
        print("{} Does not exist!".format(targetConfigFile))
        sys.exit(1)

    print("Config for\n\tstep {} and\n\thash {}:\n".format(config["step"], config["cHash"]))
    with open(targetConfigFile, "r") as f:
        targetConfig = json.load(f)
            
    pprint.pprint(targetConfig)
