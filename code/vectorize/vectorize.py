import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import json
import re
import util.util as util
import vectorizeHelpers
import scipy.sparse

from nltk.stem import PorterStemmer
from nltk.stem import LancasterStemmer
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

    config["src"] = os.path.join(
        config["sample"]["outputDir"],
        "..",
        config["vectorize"]["sampleHash"],
        config["vectorize"]["type"]
    )
    config["dataInputRegexCompiled"] = re.compile(config["vectorize"]["dataInputRegex"])

    config["regex"] = {}
    for regex, replacement in config["vectorize"]["replace"].items():
        config["regex"][replacement] = re.compile(regex)

    if config["vectorize"]["stemming"] == "porter":
        config["stemmer"] = PorterStemmer()
    if config["vectorize"]["stemming"] == "lancaster":
        config["stemmer"] = LancasterStemmer()
    return config

if __name__ == "__main__":
    config = prepare()
    config["logger"].info(
        "Starting vectorize with config {}".format(config["vectorize"]["hash"])
    )
    corpus = vectorizeHelpers.loadSample(config)
    data = vectorizeHelpers.ngramVectorize(config, corpus)
    scipy.sparse.save_npz(os.path.join(config["vectorize"]["outputDir"],"data.npz"), data)
