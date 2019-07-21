from util.util import loadConfig, getLabels, int2bv
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
# get x,y
df = pd.read_csv(
    "../data/processed/clean/8dd44a74473a038c10ff41b42e42048f5e567597c5cfbe0217244ea28d154d48/useable.csv",
    index_col=0)
config = loadConfig("../config/configtest.json")

kwargs = {
    'ngram_range': config["vectorize"]["ngramRange"],
    'dtype': np.float64,
    'strip_accents': 'unicode',
    'decode_error': 'replace',
    'analyzer': config["vectorize"]["tokenMode"],
    'min_df': config["vectorize"]["minDocFreq"]
}
vectorizer =  TfidfVectorizer(**kwargs)
x = vectorizer.fit_transform(df["payload"])
df['labelsI'] = df.labels.apply(lambda x: int2bv(x, 21)[1:]).tolist()

# get how often an item has n labels:
df['numberOfLabels'] = df.labelsI.apply(lambda x: x.sum())
df.groupby('numberOfLabels').numberOfLabels.count()
# Create an "interlap" df for 2ds:
columns = getLabels(config)[1:]
rows = { i: columns[i] for i in range(0,len(columns)) }
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
counts = pd.DataFrame(t)
counts.columns = columns
counts.rename(index = rows, inplace=True)
counts.to_csv('count.csv')
ssf = pd.Series(np.diag(counts))
df['bl'] = df.labelsI.apply(lambda x: getBestLabel(ssf, x))
