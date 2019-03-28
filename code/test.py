from tensorflow.python.keras import models
from util import load_sample, ngram_vectorize
import pprint
from sklearn.feature_extraction.text import TfidfVectorizer

NGRAM_RANGE = (1, 2)
TOKEN_MODE = 'word'
MIN_DOCUMENT_FREQUENCY = 2

((train_texts, train_labels), (test_texts, test_labels)) = load_sample("../data/dmax", mode="all")
model = models.load_model('dmaxAll_mlp.model.h5')
print("Load sample")
((train_texts, train_labels), (test_texts, test_labels)) = load_sample("../data/dmax", mode="all")
print("sample loaded")


# Learn vocabulary from training texts and vectorize training texts.

x_train, x_test = ngram_vectorize(
        train_texts, train_labels, test_texts)

results = model.evaluate(x_test, test_labels)

pprint.pprint(results)

cfm = tf.math.confusion_matrix(
        train_labels,
        predictions,
        num_classes = 22)


#predictions = model.predict(test_texts)


