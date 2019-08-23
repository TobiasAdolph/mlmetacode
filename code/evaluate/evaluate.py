import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from scipy.sparse import load_npz
from util.util import loadConfig, getDictHash, setupLogging
from os.path import join, exists
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import fbeta_score, make_scorer
import pandas as pd
from importlib import import_module
import argparse
import itertools as it
from pprint import pformat

def prepare():
    parser = argparse.ArgumentParser(
        description='EVALUATE a model/param_grid/data bundle'
    )
    parser.add_argument('--config',
            required = True,
            help = "File with the configuration, must contain key 'evaluate'")

    args = parser.parse_args()
    config = loadConfig(args.config)
    print("Starting evaluate with config {}".format(config["evaluate"]["hash"]))
    config["logger"] = setupLogging(config, "evaluate")

    config["scoring"] = {
        "fhalf": make_scorer(fbeta_score, beta=0.5, average="micro"),
        "fone": make_scorer(fbeta_score, beta=1, average="micro"),
        "ftwo": make_scorer(fbeta_score, beta=2, average="micro")
    }
    config["target"] = join(config["base"]["outputDir"], "evaluation.csv")
    return config

def getUndoneParamCombinations(config, df, param_grid):
    if not "hash" in df.columns:
        return param_grid
    keys = param_grid[0].keys()
    values = (param_grid[0][key] for key in keys)
    pcs = [dict(zip(keys, c)) for c in it.product(*values)]
    undone_pcs = []
    for pc in pcs:
        pcHash = getDictHash(pc)[0:30]
        # check if pc exists in df, if not append
        if not df[df["hash"] == pcHash].hash.any():
            config["logger"].info(
                "{} ({}) has already been evaluated, delete the row to force re-evaluation".format(
                    pcHash,
                    pformat(pc, indent=4)
                )
            )
            undone_pcs.append(pc)
    undone_param_grid = {}
    for key in keys:
        undone_param_grid[key] = set()
    for upc in undone_pcs:
        for key, value in upc.items():
            undone_param_grid[key].add(value)
    for key in keys:
        if not undone_param_grid[key]:
            del undone_param_grid[key]
        else:
            undone_param_grid[key] = list(undone_param_grid[key])
    return [undone_param_grid]


if __name__ == "__main__":
    config = prepare()
    x_train = load_npz(join(config["vectorize"]["outputDir"], "x_train.npz"))
    y_train = load_npz(join(config["vectorize"]["outputDir"], "y_train.npz"))
    results = []
    df = pd.DataFrame()
    if exists(config["target"]):
        df = pd.read_csv(config["target"], index_col=0)

    for m in config["evaluate"]["models"]:
        module = import_module(m["package"])
        class_ = getattr(module, m["name"])
        model = class_()
        if m["multilabel"] != "true":
            from sklearn.multiclass import OneVsRestClassifier
            model = OneVsRestClassifier(model)
            keys = m["param_grid"][0].keys()
            new_param_grid = {}
            for key in keys:
                new_param_grid["estimator__"+key] = m["param_grid"][0][key]
            m["param_grid"] = [new_param_grid]
        param_grid = getUndoneParamCombinations(config, df, m["param_grid"])
        if len(param_grid[0].keys()) == 0:
            config["logger"].info(
                    "All param_grid combinations have been testet for model {}".format(
                        m["name"]
                    )
            )
            continue
        for key, value in m["params"].items():
            setattr(model, key, value)


        config["logger"].info("Starting evaluate model {}".format(m["name"]))
        config["logger"].info("with this param_grid:\n{}".format(pformat(param_grid, indent=4)))
        gscv = GridSearchCV(
                model,
                param_grid,
                cv=config["evaluate"]["cv"],
                scoring=config["scoring"],
                n_jobs=-1,
                verbose=10,
                refit=False
        )
        gscv.fit(x_train, y_train.toarray())


        for idx,p in enumerate(gscv.cv_results_["params"]):
            row = {
                    "model": m["name"],
                    "hash": getDictHash(p)[0:30],
                    "params": p,
                    "vHash": config["vectorize"]["hash"]
            }
            for score in config["scoring"].keys():
                for key in (
                        'mean_fit_time',
                        'std_fit_time',
                        'mean_score_time',
                        'std_fit_time',
                        'mean_test_' + score,
                        'std_test_' + score):
                    row[key] = gscv.cv_results_[key][idx]
            results.append(row)

        cur_df = pd.DataFrame(results)
        if len(df) == 0:
            df = cur_df
        else:
            df = pd.concat([df, cur_df])

        df.to_csv(config["target"])
        config["logger"].info("Stored information of evaluation run to\n\t{}".format(config["target"]))
