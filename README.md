# Entity Linking in Queries: Efficiency vs. Effectiveness

This repository contains resources developed within the following paper:

	F. Hasibi, K. Balog, and S.E. Bratsberg. “Entity Linking in Queries: Efficiency vs. Effectiveness”,
	In proceedings of 39th European Conference on Information Retrieval (ECIR ’17), April 2017.

You can check the [paper](http://hasibi.com/files/ecir2017-elq.pdf) and [presentation](http://www.slideshare.net/FaeghehHasibi/ecir2017-elq) for detailed information.

The repository is structured as follows:

- `nordlys/`: Code required for running all the experiments
- `data/`: Query set and data required for running the code
- `qrels/`: Qrels files for ERD and Y-ERD test collections
- `runs/`: Run files reported in the paper
- `scripts/`: Run and evaluation scripts


## Code

Check the `nordlys/erd/` for the implementation of *''candidate entity ranking''* and *''disambiguation''* methods.
To generate each of the runs, check `scripts/run_scripts.sh`.

Python v2.7 is required for running the code.


## Data

The index and surface form dictionary required for running this code are described in the paper. You can also contact the authors to get them directly. The following files under the `data` folder are also required for running the code:

- `Y-ERD.tsv`: The Y-ERD test collection
- `Trec_beta*.txt`: The ERD test collection
-  `fb_dbp_snapshot.txt`: The Freebase snapshot provided by the [ERD challenge 2014](http://sigir.org/files/forum/2014D/p063.pdf)

## Qrels

There are two groups of qrels files, used for 1) *''candidate entity ranking''*, and 2) *''disambiguation''* steps.
The `qrels/*_trec.qrels` files belong to the first group, and `qrels/*_elq.qrels` files belong to the second one.


## Citation

If you use the resources presented in this repository, please cite:

```
@inproceedings{Hasibi:2017:ELQ, 
   author =    {Hasibi, Faegheh and Balog, Krisztian and Bratsberg, Svein Erik},
   title =     {Entity Linking in Queries: Efficiency vs. Effectiveness},
   booktitle = {Proceedings of 39th European Conference on Information Retrieval},
   series =    {ECIR '17},
   year =      {2017},
   pages=      {xx--xx},
   publisher = {Springer},
   DOI =       {ttp://dx.doi.org/xx}
} 
```

## Contact

If you have any questions, feel free to contact *Faegheh Hasibi* at <faegheh.hasibi@ntnu.no>.
