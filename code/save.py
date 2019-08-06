from util.util import loadConfig, getLabels, int2bv, getBestLabel
import pandas as pd
import numpy as np
import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import f_classif
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import fbeta_score, precision_recall_fscore_support

# Get all x,y
# Vectorize it
# Split x,y in test/train

df = pd.read_csv(
    "../data/processed/clean/8dd44a74473a038c10ff41b42e42048f5e567597c5cfbe0217244ea28d154d48/useable.csv",
    index_col=0)
config = loadConfig("../config/configtest.json")
# def prep(df):
df['labelsI'] = df.labels.apply(lambda x: int2bv(x, 21)[1:]).tolist()
# get how often an item has n labels:
df['numberOfLabels'] = df.labelsI.apply(lambda x: x.sum())
df.groupby('numberOfLabels').numberOfLabels.count()
# Create an "interlap" df for 2ds:
labels = getLabels(config)[1:]
t = np.zeros((20,20), np.int32)
for i in range(0,20):
    label = i + 1
    for j in range(0,20):
        if j < i:
            continue
        clabel = j + 1
        mask = 0
        mask |= 1 << label
        mask |= 1 << clabel
        t[i][j] = df[df.labels & mask == mask].labels.count()
rows = { i: labels[i] for i in range(0,len(labels)) }
counts = pd.DataFrame(t)
counts.columns = range(1,21)
counts.rename(index = rows, inplace=True)
counts.to_csv('count.csv')
ssf = pd.Series(np.diag(counts))
df['bl'] = df.labelsI.apply(lambda x: getBestLabel(ssf, x))
df.to_csv('useablet.csv')

stop_words = [
    "00",
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "07",
    "08",
    "09",
    "a",
    "across",
    "about",
    "after",
    "aim",
    "all",
    "also",
    "among",
    "an",
    "and",
    "any",
    "approach",
    "are",
    "argue",
    "argues",
    "article",
    "as",
    "at",
    "author",
    "authors",
    "be",
    "because",
    "been",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "chesterrep",
    "click",
    "conclusion",
    "conclusions",
    "conference",
    "content",
    "com",
    "data",
    "dataset",
    "discuss",
    "discusses",
    "do",
    "due",
    "during",
    "each",
    "eight",
    "evaluate",
    "evaluates",
    "figshare",
    "file",
    "find",
    "finds",
    "findings",
    "first"
    "five",
    "for",
    "found",
    "four",
    "from",
    "further",
    "go",
    "going",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "his",
    "how",
    "however",
    "http",
    "https",
    "if",
    "in",
    "include",
    "includes",
    "including",
    "into",
    "introduction",
    "is",
    "it",
    "item",
    "its",
    "journal",
    "kb",
    "like",
    "link",
    "make",
    "many",
    "may",
    "metadata",
    "method",
    "methodological",
    "methods",
    "more",
    "moreover",
    "most",
    "much",
    "near",
    "nine",
    "no",
    "non",
    "not",
    "objective",
    "of",
    "on",
    "one",
    "only",
    "or",
    "org",
    "other",
    "our",
    "out",
    "over",
    "paper",
    "phd",
    "please",
    "proceeding",
    "project",
    "publish",
    "published",
    "publishing",
    "publication",
    "rather",
    "records",
    "research",
    "respectively",
    "review",
    "reviewed",
    "same",
    "seven",
    "she",
    "should",
    "show",
    "shows",
    "showed",
    "six",
    "six",
    "so",
    "some",
    "studies",
    "study",
    "such",
    "supplemental",
    "supplementary",
    "ten",
    "text",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "thesis",
    "they",
    "this",
    "those",
    "thoroughly",
    "three",
    "through",
    "to",
    "tutorial",
    "tutorials",
    "two",
    "under",
    "university",
    "url",
    "use",
    "used",
    "using",
    "was",
    "we",
    "well",
    "were",
    "what",
    "when",
    "where",
    "whether",
    "which",
    "while",
    "who",
    "why",
    "will",
    "with",
    "within",
    "work",
    "worked",
    "would",
    "www",
    "you",
    "your",
]
kwargs = {
    'ngram_range': [1,2],
    'dtype': np.float64,
    'strip_accents': 'unicode',
    'decode_error': 'replace',
    'analyzer': config["vectorize"]["tokenMode"],
    'min_df': config["vectorize"]["minDocFreq"],
    'max_df': df.groupby("bl").bl.count().max()/len(df),
    'stop_words': stop_words
}
vectorizer =  TfidfVectorizer(**kwargs)
x = vectorizer.fit_transform(df["payload"])
# Kbest:
# n_labels * 25 /100 1/15
topK = len(labels) * 250
# n_features/100
topK = math.floor(x.shape[1]/100)
def get_selected_vocabulary_and_scores(vocab, selector):
     retval = []
     keys = list(vocab.keys())
     values = list(vocab.values())
     for idx in selector.get_support(indices=True):
         ngram = keys[values.index(idx)]
         score = selector.scores_[idx]
         if len(retval) == 0:
             retval.append([ngram, score])
             continue
         for i in range(0,len(retval)+1):
             if i >= len(retval):
                 retval.append([ngram, score])
                 break
             if retval[i][1] < score:
                 retval.insert(i, [ngram, score])
                 break
     return retval

selector = SelectKBest(f_classif, k=min(topK, x.shape[1]))
selector.fit(x, df.bl)
x =  selector.transform(x).astype(np.float64)
x_train, x_test, y_train, y_test = train_test_split(xs, df.labelsI.values.tolist(), stratify=df.bl)

neigh = KNeighborsClassifier(n_neighbors=25)
neigh.fit(x_train, y_train)
y_pred = neigh.predict(x_test)
y_test = np.array(y_test)

fbeta_score(y_test, y_pred, average='micro', beta=0.5) # classifier => stress precision
fbeta_score(y_test, y_pred, average='micro', beta=1)   # assistant => equilibrium
fbeta_score(y_test, y_pred, average='micro', beta=2.0) # sampler => stress recall
# Show label-wise
precision_recall_fscore_support(y_test, y_pred, average=None, beta=0.5, labels=range(0,20)) # classifier
precision_recall_fscore_support(y_test, y_pred, average=None, beta=1.0, labels=range(0,20)) # assistant
precision_recall_fscore_support(y_test, y_pred, average=None, beta=2.0, labels=range(0,20)) # sampler
# Show unweighted average
precision_recall_fscore_support(y_test, y_pred, average="micro", beta=1.0, labels=range(0,20))
# parameter_space for trees and forests
