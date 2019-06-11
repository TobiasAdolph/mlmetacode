import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import json
import math
import random
import string
import statistics
import util.util as util
import pandas as pd
import numpy as np

def prepare():
    parser = argparse.ArgumentParser(
        description='SAMPLE: sample from cleaned data.'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'sample'")
    args = parser.parse_args()
    config = util.loadConfig(args.config)
    config["logger"] = util.setupLogging(config, "sample")
    config["src"] = os.path.join(
        config["clean"]["baseDir"],
        config["sample"]["cleanHash"],
        "useable.h5"
    )
    config["labels"]  = util.getLabels(config)
    return config

if __name__ == "__main__":
    config = prepare()
    print("Starting sample with config {}".format(config["sample"]["hash"]))
    store = pd.HDFStore(config["src"])
    df = store["r"]
    store.close()
    df["selected"] = [False] * len(df)
    df["selectedAs"] = [""] * len(df)
    df["label"] = 0 * len(df)
    config["logger"].info("Sample loaded")
    sizes = [ len(df[df[str(i)]]) for i in range(1, len(config["labels"]))]
    if config["sample"]["type"] == "max":
        config["sample"]["size"] = max(sizes)
    elif config["sample"]["type"] == "min":
        config["sample"]["size"] = min(sizes)
    elif config["sample"]["type"] == "median":
        config["sample"]["size"] = math.floor(statistics.median(sizes))
    elif config["sample"]["type"] == "mean":
        config["sample"]["size"] = math.floor(statistics.mean(sizes))
    else:
        config["sample"]["type"] += str(config["sample"]["size"])

    config["logger"].info("\tMode: {}\n\tSize: {}".format(config["sample"]["type"],
                                                          config["sample"]["size"]))

    config["sample"].setdefault("seed", random.randint(0,999999999))
    config["logger"].info("Using seed {} to pick".format(config["sample"]["seed"]))
    result = []
    for i in range(1, len(config["labels"])):
        totalSampleSize = min(sizes[i-1], config["sample"]["size"])
        trainSampleSize = math.floor(totalSampleSize * config["sample"]["ratio1"])
        valSampleSize = math.floor(totalSampleSize * config["sample"]["ratio2"]) - trainSampleSize
        testSampleSize = valSampleSize
        while trainSampleSize + 2 * valSampleSize < totalSampleSize:
            config["logger"].warning("Sample size is not fully exploited!")
            trainSampleSize += 1
        config["logger"].info("Train: {}".format(trainSampleSize))
        config["logger"].info("Vald: {}".format(valSampleSize))
        config["logger"].info("Test: {}".format(testSampleSize))
        config["logger"].info("Total: {}".format(totalSampleSize))

        sample = df[df[str(i)]].sample(n=totalSampleSize,
                                       random_state=config["sample"]["seed"])
        sample.selected = True
        sampleTrain = sample.sample(n=trainSampleSize,
                                    random_state=config["sample"]["seed"])
        sampleTrain.selectedAs = "train"
        sample.update(sampleTrain)
        sampleVal = sample[sample["selectedAs"] == ""].sample(
            n=valSampleSize, random_state=config["sample"]["seed"])
        sampleVal.selectedAs = "val"
        sample.update(sampleVal)
        sampleTest = sample[sample["selectedAs"] == ""]
        sampleTest.selectedAs = "test"
        sample.update(sampleTest)
        sample.label = i
        label = {
            "total": sizes[i-1],
            "totalSampleSize": totalSampleSize,
            "trainSampleSize": trainSampleSize,
            "valSampleSize": valSampleSize,
            "testSampleSize": testSampleSize,
            "medianLength": int(sample.payload.str.len().median()),
            "maxLength": int(sample.payload.str.len().max()),
            "minLength": int(sample.payload.str.len().min()),
            "meanLength": int(sample.payload.str.len().mean())
        }
        config["logger"].info("Picked {} out of {} for {}".format(
            label["totalSampleSize"],
            label["total"],
            config["labels"][i]
        ))
        df.update(sample)
        result.append(label)

    with open(os.path.join(
        config["sample"]["outputDir"],  "statistics.json"), "w") as f:
        json.dump(result, f)
    sampleLoc = os.path.join(config["sample"]["outputDir"], "sample.h5")
    store = pd.HDFStore(sampleLoc)
    sampleDf = df[df.selected][["payload", "label", "selectedAs"]].copy()

    store["sample"] = sampleDf
    store.close()
    config["logger"].info("Saved sample of type {} with overall size {} to {}".format(
        config["sample"]["type"],
        len(sampleDf),
        sampleLoc
    ))
