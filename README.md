# ML

## Dimensions:
* Data selection:
    * Dmin: Take the smallest discipline database and sample all other to that size (poster)
    * Dstat: Take value = n (e.g. 1000) and sample all to that size or the highest possible size
    * Dmax: Take all data from all disciplines
* Train/evaluate ratio:
    * 80/20 (poster)
    * 50/50
* Field selection:
    * titles (poster)
    * descriptions
    * titles and descriptions

## Statistics:
Retrieval of Statistics as proposed [here](https://developers.google.com/machine-learning/guides/text-classification/step-2).

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
```
