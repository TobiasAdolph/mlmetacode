import os
import json
import pandas as pd
import util
import argparse
import json

def get_base_data(config):
    df = pd.read_csv(os.path.join(config["clean"]["baseDir"], config["vectorize"]["cleanHash"], "result.csv"), low_memory=False)
    udf = pd.read_csv(os.path.join(config["clean"]["baseDir"], config["vectorize"]["cleanHash"], "useable.csv"), low_memory=False)
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
            "labelCardinality": sum(udf.nol)/len(udf),
            "labelDensity": sum(udf.nol)/(len(udf)*len(util.getLabels(config)[1:])),
            "special": udf[udf.special].id.count(),
            "allFeatures": info["allFeatures_bow"],
            "noTrain": info["noTrain"],
            "noTest": info["noTest"],
            "noTrain_train": info["noTrain_train"],
            "noTrain_val": info["noTrain_val"],
            "noStopWords": len(stopWords),
            "wc_mean": udf.wc.mean(),
            "wc_median": udf.wc.median(),
            "wc_first_quartile": udf.wc.quantile(.25)
        }
    ]


def get_schemes_data(config):
    data = []
    df = pd.read_csv(os.path.join(config["clean"]["baseDir"], config["vectorize"]["cleanHash"], "useable.csv"), low_memory=False)
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
    df = pd.read_csv(os.path.join(config["clean"]["baseDir"], config["vectorize"]["cleanHash"], "useable.csv"), low_memory=False)
    for idx, label_name in enumerate(label_names):
        label_no = idx + 1
        data.append({
            "name":         label_name,
            "1-label":      df[df.labels == 2**label_no].id.count(),
            "2-labels":     df[df.labels & 2**label_no == 2**label_no][df.nol == 2].id.count(), 
            "geq-3-labels": df[df.labels & 2**label_no == 2**label_no][df.nol >= 3].id.count(), 
            "nol_mean":     df[df.labels & 2**label_no == 2**label_no].nol.mean(), 
            "blcount":      df.groupby(df.bl).bl.count().iloc[idx],
            "total":        df[df.labels & 2**label_no == 2**label_no].id.count(), 
            "percentage":   df[df.labels & 2**label_no == 2**label_no].id.count()/df.id.count(),
            "wc_mean":      df[df.labels & 2**label_no == 2**label_no].wc.mean(),
            "wc_median":      df[df.labels & 2**label_no == 2**label_no].wc.median()
        })
    data.append(
        {
            "name": "total", 
            "1-label": df[df.nol == 1].id.count(), 
            "2-labels": df[df.nol == 2].id.count(),
            "geq-3-labels": df[df.nol >= 3].id.count(),
            "nol_mean":     df.nol.mean(), 
            "blcount": 0,
            "total": df.id.count(),
            "percentage": 1.0,
            "wc_mean":      df.wc.mean(),
            "wc_median":    df.wc.median()
        }
    )
    return data

def getVHash(size):
    if size == "s":
        return "09056be8ca8df0a3c396526f38db974541d7d45d6e25e950329be050e04b99e1"
    elif size == "m":
        return "346cbc992bbea0fd68de2863dd86c7487a65c60f782e2201b92c5c122f7e4460"
    elif size == "l":
        return "46e4d08f373ee10bec65345c078974f0dfb2afc1236e1bf59a26c098f82631b4"

def getSize(vHash):
    if vHash == "09056be8ca8df0a3c396526f38db974541d7d45d6e25e950329be050e04b99e1":
        return "s"
    elif vHash == "346cbc992bbea0fd68de2863dd86c7487a65c60f782e2201b92c5c122f7e4460":
        return "m"
    elif vHash == "46e4d08f373ee10bec65345c078974f0dfb2afc1236e1bf59a26c098f82631b4":
        return "l"

def get_labels_score(config):
    data =  []
    scores = [
            "fhalf",
            "fone",
            "ftwo"
    ]
    label_names = util.getLabels(config)[1:]
    df = pd.read_csv(os.path.join(config["evaluate"]["baseDir"], "evaluation.csv"))
    maxRows = {}
    for score in scores:
        maxRows[score] = df.nlargest(1, score + "_all_macro")
        maxRows[score + "_lstm"] = df[df.model == "LSTMClassifier"].nlargest(1, score + "_all_macro")
    for idx, label_name in enumerate(label_names):
        row = {"name": label_name}
        for score in scores:
            key = score  + "_" + str(idx)
            row[score] = float(maxRows[score][key])
            row[score + "_size"] = getSize(str(maxRows[score]["vHash"].iloc[0]))
            row[score + "_model"] = str(maxRows[score]["model"].iloc[0])
            row[score + "_lstm"] = float(maxRows[score+"_lstm"][key])
        data.append(row)
    return data


def get_models_agg(config):
    agg_values = [
            "fhalf_all_macro",
            "fhalf_all_micro",
            "fone_all_macro",
            "fone_all_micro",
            "ftwo_all_macro",
            "ftwo_all_micro",
            "wiki_diag"
    ]
    data = []
    df = pd.read_csv(os.path.join(config["evaluate"]["baseDir"], "evaluation.csv"))
    for model in pd.unique(df.model):
        for size in ("s", "m", "l"):
            row = {
                "model": model,
                "size": size
            }
            vHash = getVHash(size)
            for agg_value in agg_values:
                row["count"] = len(df[df.model == model][df.vHash == vHash])
                dfRow = df[df.model == model][df.vHash == vHash].nlargest(1, agg_value)
                if len(dfRow) == 0:
                    row[agg_value] = 0.0
                else:
                    row[agg_value] = float(dfRow[agg_value])
            data.append(row)
    return data

def default_function(config):
    print("No function by the name {}".format(config["req_collect"]))

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
        "labels": get_labels_data,
        "models2agg": get_models_agg,
        "labels2score": get_labels_score
    }

    config = util.loadConfig(args.config)
    config["req_collect"] = args.collect
    config["target"] = args.target

    config["collect_function"] = (
        collect_functions.get(
            args.collect,
            default_function 
        )
    )

    config["labels"]  = util.getLabels(config)
    return config


if __name__ == "__main__":
    config = prepare()
    data = pd.DataFrame(config["collect_function"](config))
    data.to_csv(config["target"], index=False)
