import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import json
import re
import util.util as util
import vectorizeHelpers
import glob
import pandas as pd

def prepare():
    parser = argparse.ArgumentParser(
        description='VECTORIZE the sampled data'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'vectorize'")

    args = parser.parse_args()
    config = util.loadConfig(args.config)
    config["logger"] = util.setupLogging(config, "vectorize")
    config["src"] = os.path.join(config["sample"]["baseDir"],
                 config["vectorize"]["sampleHash"],
                "sample.h5"
    )
    return config

if __name__ == "__main__":
    config = prepare()
    print("Starting vectorize with config {}".format(config["vectorize"]["hash"]))
    store = pd.HDFStore(config["src"])
    corpus = store["sample"]
    store.close()
    (vectorizer, selector, x) = vectorizeHelpers.getVectorizerAndSelector(config, corpus)
    config["logger"].info("Vectorizing {}".format(config["src"]))

    for selectedAs in ("train", "val", "test"):
        vectorizeHelpers.vectorizeAndSave(config, corpus, selectedAs, vectorizer, selector)

    vectorizeHelpers.dumpBinary(
        config,
        "vectorizer.bin",
        vectorizer)
    vectorizeHelpers.dumpBinary(
        config,
        "selector.bin",
        selector)
