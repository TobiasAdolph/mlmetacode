import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import retrieveHelpers
from concurrent.futures import ProcessPoolExecutor
from ctypes import c_bool
import multiprocessing as mp
from datetime import datetime
import argparse
import json
import re


parser = argparse.ArgumentParser(
    description='RETRIEVE: retrieve all raw data with a given configuration.'
)

parser.add_argument('--config',
        required    = True,
        help        = "File with the configuration for the training run")

args = parser.parse_args()

if not os.path.isfile(args.config):
    print("{} is not a path to a file".format(args.config))

with open(args.config, "r") as f:
    config = json.load(f)


print("Starting {} workers".format(len(config["hvs"])))

targetDir = os.path.join(config["hvDataBaseDir"],
                            datetime.today().strftime('%Y-%m-%d'),
                            "raw")


if not os.path.isdir(targetDir):
    os.mkdir(targetDir)
config["targetDir"] = targetDir

hvConfigRegex = re.compile(config["hvConfigRegex"])
workpackage = [(config, os.path.join(config["hvConfigDir"], f)) for f in os.listdir(config["hvConfigDir"]) if hvConfigRegex.match(f)]

#retrieveHelpers.doHarvest(workpackage[0])
hvs = mp.Array(c_bool, [True]*len(config["hvs"]))

with ProcessPoolExecutor(
    max_workers=len(config["hvs"]),
    initializer = retrieveHelpers.init_globals,
    initargs = (hvs, )
) as ex:
    res = zip(workpackage, ex.map(retrieveHelpers.doHarvest, workpackage))
