import os
import json
import pandas as pd
import util.util as util

def get_schemes_data(config):
    schemes_data = []
    with open(os.path.join(config["base"]["configDir"], "schemes.json"), "r") as f:
        schemes = json.load(f)
    df = pd.read_csv(os.path.join(config["clean"]["outputDir"]), "useable.csv")
    for scheme, value in schemes.items():
        schemes_data.append(
            {
                "name": value["long"],
                "count": df[pd.notna(df[scheme])][scheme].count()
            }
        )
    return schemes_data

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

    collect_functions = {
        "schemes": get_schemes_data
    }

    config = util.loadConfig(args.config)
    config["req_collect"] = args.collect
    config["target"] = args.target

    config["collect_function"] = (
        collect_functions.get(
            args.data,
            lambda config: print(
                "No function by the name {}".format(config["req_collect"])
            )
        )
    )
    config["labels"]  = util.getLabels(config)
    config["schemes"] = util.getSchemes(config)


if __name__ == "__main__":
    config = prepare()
    data = pd.DataFrame(config["collect_function"](config))
    data.to_csv(config["target"])
