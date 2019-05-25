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
import util.util as util

def prepare():
    parser = argparse.ArgumentParser(
        description='RETRIEVE: retrieve all raw data.'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'retrieve'")
    parser.add_argument('--sleep',
            default = 20,
            help = "Time period to sleep until a harvester is checked during harvesting")
    args = parser.parse_args()
    config = util.loadConfig(args.config)
    config["retrieve"]["sleep"] = int(args.sleep)
    config["logger"] = util.setupLogging(config, "retrieve")
    return config

if __name__ == "__main__":
    config = prepare()
    config["logger"].info(
        "Starting retrieve with config {}".format(config["retrieve"]["hash"])
    )

    # Setup work
    workpackage = []
    config["retrieve"]["hvConfigRegexCompiled"] = re.compile(config["retrieve"]["hvConfigRegex"])
    config["logger"].info("Load hvConfigs from {}".format(config["retrieve"]["configDir"]))
    for f in os.listdir(config["retrieve"]["configDir"]):
        if config["retrieve"]["hvConfigRegexCompiled"].match(f):
            workpackage.append((config, os.path.join(config["retrieve"]["configDir"],f)))
    # And distribute it
    # hvs is necessary to safeguard against race conditions)
    hvs = mp.Array(c_bool, [True]*len(config["retrieve"]["hvs"]))
    config["logger"].info("Starting {} workers".format(len(config["retrieve"]["hvs"])))
    with ProcessPoolExecutor(
        max_workers=len(config["retrieve"]["hvs"]),
        initializer = retrieveHelpers.init_globals,
        initargs = (hvs, )
    ) as ex:
        res = zip(workpackage, ex.map(retrieveHelpers.doHarvest, workpackage))
    for r in res:
        if r[1]:
            config["logger"].debug("Success for {}: {}".format(r[0][1], r[1]))
        else:
            config["logger"].warn("Unsuccesful run for {}".format(r[0][1]))
