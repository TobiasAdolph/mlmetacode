# Classification of Research Discipline based on DataCite Metadata with Supervised Learning 

## TODO

### Data
* Bigger training set
    * check whether datacite offers a better API to retrieve the training set
    * Rerun data retrieval with newer version of harvester lib
	* Allow to include datasets which do not have descriptions
    * Find data sources for underrepresented disciplines
    * Add Metrics for enlaregd data set

* Better training set
    * Use more fields than title and description
	* Check for multiple titles/descriptions
* Make use of data set which are annotated with multiple categories

### Code
* separate code in the following steps
    * retrieve
    * clean
    * sample
    * train
    * test/evaluate
    * use
* Document steps (see down this document) to make them reproducible
* tune simple model https://developers.google.com/machine-learning/guides/text-classification/step-5
* Improve language checks (research)
* clean out short descriptions, short titles? 
* Other, more mature approaches than ngrams (grammar, NLP):
  https://developers.google.com/machine-learning/guides/text-classification/step-2-5 schlägt als Alternative

### Other
    * Bias: Document where we could be biased, where it is unevitable and where it can be mitigated
    * Literature research: Papers reporting multi-categorical text classification
    * Decide on Journal/Conference
    * Add stub for paper
    * Discuss uploading to ArXiv

## Documentation 
* Data selection:
    * Dmin: Take the smallest discipline database and sample all other to that size (poster)
    * Dstat: Take value = n (e.g. 1000) and sample all to that size or the highest possible size
    * Dmed: Take median size of categories and sample all to that size or the highest possible size
    * Dmax: Take all data from all disciplines
* Train/evaluate/test:
    * 80/10/10 (poster)
    * ?/?/?
* Field selection:
    * titles 
    * descriptions
    * titles and descriptions (poster)

## Statistics:
Retrieval of Statistics [based on this suggsestion](https://developers.google.com/machine-learning/guides/text-classification/step-2).

### Dmin
| Metric name                           | Metric value   |
| ------------------------------------- | --------------:|
| Number of samples                     |         4378   |
| Number of classes                     |           22   |
| Number of samples per class           |          199   |
| Number of words per sample (title)    |           60   |
| Number of words per sample (descr)    |          271   |
| Number of words per sample (t+d)      |          255.5 |

### Dstat1000
| Metric name                           | Metric value |
| ------------------------------------- | ------------:|
| Number of samples                     |        19452 |
| Number of classes                     |           22 |
| Number of samples per class           |     199-1000 |
| Number of words per sample (title)    |           63 |
| Number of words per sample (descr)    |          264 |
| Number of words per sample (t+d)      |          347 |

### Dmed

### Dmax
| Metric name                           | Metric value |
| ------------------------------------- | ------------:|
| Number of samples                     |       399568 |
| Number of classes                     |           22 |
| Number of samples per class           |   199-209052 |
| Number of words per sample (title)    |           45 |
| Number of words per sample (descr)    |           79 |
| Number of words per sample (t+d)      |          126 |

## Code

```bash
virutalenv -p `which python3` venv
source venv/bin/activate
pip install -r requirements.txt

# Extract & clean data
```

