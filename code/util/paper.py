import os
import json
import pandas as pd
import util.util as util
import argparse
import json

def get_base_data(config):
    df = pd.read_csv(os.path.join(config["clean"]["outputDir"], "result.csv"), low_memory=False)
    udf = pd.read_csv(os.path.join(config["clean"]["outputDir"], "useable.csv"), low_memory=False)
    with open(os.path.join(config["vectorize"]["outputDir"], "info.json"), "r") as f:
        info = json.load(f)
    stopWords = util.getStopWords(config)
    
    return [
        {
            "all": df.id.count(),
            "annot": df[~df.notAnnot].id.count(),
            "payloadMinLength": config["clean"]["payloadMinLength"],
            "duplicates": df[~df.notAnnot][df.duplicate].id.count(),
            "useable": udf[udf.useable].id.count(),
            "labelsets": udf.labels.nunique(),
            "labelsetsOnce": udf.groupby(df.labels).labels.count().value_counts().get(1),
            "special": udf[udf.special].id.count(),
            "allFeatures": info["allFeatures"],
            "noTrain": info["noTrain"],
            "noTest": info["noTest"],
            "noStopWords": len(stopWords)
        }
    ]


def get_schemes_data(config):
    data = []
    df = pd.read_csv(os.path.join(config["clean"]["outputDir"], "useable.csv"), low_memory=False)
    for scheme, value in util.getSchemes(config).items():
        data.append(
            {
                "name": value["long"],
                "count": df[pd.notna(df[scheme])][scheme].count()
            }
        )
    return sorted(data, key=lambda i:(i["count"]), reverse=True)

def get_labels_data(config):
    data =  []
    label_names = util.getLabels(config)[1:]
    df = pd.read_csv(os.path.join(config["clean"]["outputDir"], "useable.csv"), low_memory=False)
    for idx, label_name in enumerate(label_names):
        label_no = idx + 1
        data.append({
            "name":         label_name,
            "1-label":      df[df.labels == 2**label_no].id.count(), 
            "add":          df[df.labels & 2**label_no == 2**label_no][df.special].id.count(), 
            "2-labels":     df[df.labels & 2**label_no == 2**label_no][df.nol == 2].id.count(), 
            "3-labels":     df[df.labels & 2**label_no == 2**label_no][df.nol == 3].id.count(), 
            "geq-4-labels": df[df.labels & 2**label_no == 2**label_no][df.nol >= 4].id.count(), 
            "blcount":      df.groupby(df.bl).bl.count().iloc[idx],
            "total":        df[df.labels & 2**label_no == 2**label_no].id.count(), 
            "percentage":   df[df.labels & 2**label_no == 2**label_no].id.count()/df.id.count() 
        })
    data.append(
        {
            "name": "total", 
            "1-label": df[df.nol == 1].id.count(),
            "add": df[df.special].id.count(),
            "2-labels": df[df.nol == 2].id.count(),
            "3-labels": df[df.nol == 3].id.count(),
            "geq-4-labels": df[df.nol >= 4].id.count(),
            "blcount": "-",
            "total": df.id.count(),
            "percentage": 1.0 
        }
    )
    return data



def prepare():
    parser = argparse.ArgumentParser(
        description='Collect data for the paper to display'
    )

    parser.add_argument('--config',
            required    = True,
            help        ="File with the configuration")
    parser.add_argument('--collect',
            required    = True,
            help        ="Data to collect")
    parser.add_argument('--target',
            required    = True,
            help        ="Target to store the collected data to")

    args = parser.parse_args()

    collect_functions = {
        "base": get_base_data,
        "schemes": get_schemes_data,
        "labels": get_labels_data
    }

    config = util.loadConfig(args.config)
    config["req_collect"] = args.collect
    config["target"] = args.target

    config["collect_function"] = (
        collect_functions.get(
            args.collect,
            lambda config: print(
                "No function by the name {}".format(config["req_collect"])
            )
        )
    )

    config["labels"]  = util.getLabels(config)
    return config


if __name__ == "__main__":
    config = prepare()
    data = pd.DataFrame(config["collect_function"](config))
    data.to_csv(config["target"], index=False)
