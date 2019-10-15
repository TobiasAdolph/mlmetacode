# Classification of Research Discipline based on DataCite Metadata with Supervised Learning 

The procedure is divided into separate steps:
* retrieve: Get metadata from DataCite via OAI-PMH
* clean: Clean the data
* vectorize: Convert and split data into test/train set
* evaluate: Run the training and evaluation

Each of these step has a config in dir configs, which is hashed. These hashes are used
to chain the configs of the separate steps together. 
