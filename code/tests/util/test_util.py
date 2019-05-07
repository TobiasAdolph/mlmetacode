import os
import util.util as util
import numpy as np
import shutil
from train.mlp import train_ngram_model

################################################################################
# TEST PREPARATION
################################################################################
def getTestConfig():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                "config/config.json")

payload = { "test": [1,2,3], "test2": { "test3": "abc" } }
subdir = "retrieve"
config = util.loadConfig(getTestConfig())

################################################################################
# TESTS
################################################################################
def testLoadConfig():
    # Check autocompletion of config works
    config = util.loadConfig(getTestConfig())
    for key in ("hash", "rawDataDir", "processedDataDir", "configDir"):
        assert key in config.keys()

    # Check autocreations work (therefore delete the dirs first)
    hashedConfig = os.path.join(os.path.dirname(getTestConfig()),
                                       config["hash"] + ".json")
    if os.path.isfile(hashedConfig):
        os.remove(hashedConfig)
    shutil.rmtree(config["processedDataDir"])

    config = util.loadConfig(getTestConfig())
    # Check config backup works and provides identical copy
    for key in ("processedDataDir", "configDir"):
        assert os.path.isdir(config[key])
    for key in ("retrieve", "clean", "sample", "train", "evaluate", "use"):
        assert os.path.isdir(os.path.join(config["processedDataDir"], key))
    assert os.path.exists(hashedConfig)
    config2 = util.loadConfig(hashedConfig)
    assert config == config2

def testGetDictHash():
    assert util.getDictHash(payload) == "f19f5418e01b4fe2883a00bbec8f5f35138b76f1def13761d0244f531eb6b18f"

def testGetDictHash2():
    payload["test4"] = "new"
    assert util.getDictHash(payload) != "f19f5418e01b4fe2883a00bbec8f5f35138b76f1def13761d0244f531eb6b18f"

def testDumpJson():
    util.dumpJsonToFile(config, "test.json", payload)
    util.dumpJsonToFile(config, "test.json", payload, subdir)
    assert os.path.isfile(os.path.join(config["processedDataDir"], "test.json"))
    assert os.path.isfile(os.path.join(config["processedDataDir"], subdir, "test.json"))

def testLoadJson():
    payload2 = util.loadJsonFromFile(config, "test.json")
    payload3 = util.loadJsonFromFile(config, "test.json", subdir)
    assert payload2 == payload
    assert payload3 == payload
    assert payload2 == payload3

def testDumpBinary():
    util.dumpBinary(config, "test.bin", payload)
    util.dumpBinary(config, "test.bin", payload, subdir)
    assert os.path.isfile(os.path.join(config["processedDataDir"], "test.bin"))
    assert os.path.isfile(os.path.join(config["processedDataDir"], subdir,
                                       "test.bin"))

def testLoadBinary():
    payload2 = util.loadBinary(config, "test.bin")
    payload3 = util.loadBinary(config, "test.bin", subdir)
    assert payload2 == payload
    assert payload3 == payload
    assert payload2 == payload3

def testLoadTextAndLabels():
    data = util.loadTextAndLabels(config)
    assert len(data.keys()) == 22

def testLoadSample():
    # delete possibly existing cached sample
    for sampleFile in ("train.json", "test.json", "val.json"):
        sampleFilePath = os.path.join(config["processedDataDir"], "train",
                                      sampleFile)
        if os.path.isfile(sampleFilePath):
            os.remove(sampleFilePath)
    (train_texts, train_labels), (val_texts, val_labels), (test_texts, test_labels) = (
        util.loadSample(config))
    assert len(train_texts) == 176
    assert len(train_labels) == 176
    assert len(val_texts) == 22
    assert len(val_labels) == 22
    assert len(test_texts) == 22
    assert len(test_labels) == 22
    (train_texts2, train_labels2), (
        val_texts2, val_labels2), (
        test_texts2, test_labels2) = (
        util.loadSample(config)
    )
    assert train_texts == train_texts2
    assert np.array_equal(train_labels,train_labels2)
    assert val_texts == val_texts2
    assert np.array_equal(val_labels,val_labels2)
    assert test_texts == test_texts2
    assert np.array_equal(test_labels,test_labels2)

def testGetAnzsrc():
    anzsrc = util.getAnzsrc(config)
    assert len(anzsrc.keys()) == 23
    anzsrcList = util.getAnzsrcAsList(config)
    assert len(anzsrcList) == 23
    anzsrcShort = util.getShortAnzsrc(config)
    assert len(anzsrcShort) == 23
    anzsrcShortList = util.getShortAnzsrcAsList(config)
    assert len(anzsrcShortList) == 23

def testConfusionMatrix():
    text    = []
    labels  = []
    for t, l in util.loadSample(config):
       text.extend(t)
       labels.extend(l)
    data = util.ngramVectorize(text, labels, config)
    model = train_ngram_model(config)
    (test_texts, test_labels) = util.loadJsonFromFile(config, "test.json", "train")
    cfm = util.getConfusionMatrix(config, model, test_texts, test_labels)
    assert cfm.shape == (22,22)
    dfmAsDf = util.cfm2df(cfm, range(len(test_labels)))
    assert dfmAsDf.shape == (22, 22)

def testNgramVectorize():
    for binary in ("vectorizer", "selector"):
        path = os.path.join(config["processedDataDir"], "train", binary +
                            ".bin")
        if os.path.isfile(path):
            os.remove(path)
    (texts, labels) = util.loadJsonFromFile(config, "test.json", "train")
    x = util.ngramVectorize(texts, labels, config)
    assert x.shape[0] == 22
    x2 = util.ngramVectorize(texts, labels, config)
    assert x.shape == x2.shape

