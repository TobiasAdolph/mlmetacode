import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import glob
import util.util as util
import ijson
import json
import pprint
import re

def prepare():
    """ Prepares a cleaning run

    # Returns
        config: dict A configuration with all paths, compiled regexes and a
                     logger
    """
    parser = argparse.ArgumentParser(
        description='Grep over subjects of retrieved metadata records'
    )

    parser.add_argument('--config',
            required    = True,
            help        ="File with the configuration for the cleaning run")

    parser.add_argument('--field',
            default    = "value",
            choices     = ("value", "subjectScheme", "schemeURI"),
            help        ="On which field to grep on")

    parser.add_argument('--grep',
            required    = True,
            help        ="Grep expression")



    args = parser.parse_args()
    config = util.loadConfig(args.config)

    config["field"] = args.field
    config["grep"] = args.grep

    if "regex" in config["clean"].keys():
        config["regex"] = {
            "dataInput": re.compile(config["clean"]["regex"]["dataInput"]),
        }
    elif "dataInputRegex" in config["clean"].keys():
        config["regex"] = {
            "dataInput": re.compile(config["clean"]["dataInputRegex"]),
        }
    return config

if __name__ == "__main__":
    config = prepare()
    for fileName in glob.glob(
        os.path.join(config["retrieve"]["baseDir"], config["clean"]["retrieveHash"]) + "/*"):
        if config["regex"]["dataInput"].match(fileName):
            with open(fileName) as f:
                for document in ijson.items(f, 'documents.item'):
                    for subject in document["subjects"]:
                        if re.match(config["grep"], subject.get(config["field"], "")):
                            print(
                                "-------- Match for {} - {}".format(
                                    fileName,
                                    document["identifier"]["value"]
                                )
                            )
                            pprint.pprint(subject)
