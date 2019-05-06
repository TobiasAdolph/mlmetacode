import os
import util.util as util

def getTestConfig():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                "config/config.json") 

def testLoadConfig():
    config = util.loadConfig(getTestConfig())

    # Check autocompletion of config works
    for key in ("hash", "rawDataDir", "processedDataDir", "configDir"):
        assert key in config.keys()

    # Check autocreations work
    hashedConfig = os.path.join(os.path.dirname(getTestConfig()),
                                       config["hash"] + ".json")
    assert os.path.exists(hashedConfig)
    for key in ("processedDataDir", "configDir"):
        assert os.path.isdir(config[key])

    for key in ("retrieve", "clean", "sample", "train", "evaluate", "use"):
        assert os.path.isdir(os.path.join(config["processedDataDir"], key))

    # Check config backup works and provides identical copy
    config2 = util.loadConfig(hashedConfig)
    assert config == config2

payload = { "test": [1,2,3], "test2": { "test3": "abc" } }
subdir = "retrieve"

def testGetDictHash():
    assert util.getDictHash(payload) == "f19f5418e01b4fe2883a00bbec8f5f35138b76f1def13761d0244f531eb6b18f"

def testGetDictHash2():
    payload["test4"] = "new"
    assert util.getDictHash(payload) != "f19f5418e01b4fe2883a00bbec8f5f35138b76f1def13761d0244f531eb6b18f"

def testDumpJson():
    config = util.loadConfig(getTestConfig())
    util.dumpJsonToFile(config, "test.json", payload)
    util.dumpJsonToFile(config, "test.json", payload, subdir)
    assert os.path.isfile(os.path.join(config["processedDataDir"], "test.json"))
    assert os.path.isfile(os.path.join(config["processedDataDir"], subdir, "test.json"))

def testLoadJson():
    config = util.loadConfig(getTestConfig())
    payload2 = util.loadJsonFromFile(config, "test.json")
    payload3 = util.loadJsonFromFile(config, "test.json", subdir)
    assert payload2 == payload
    assert payload3 == payload
    assert payload2 == payload3

