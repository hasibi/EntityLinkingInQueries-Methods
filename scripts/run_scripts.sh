# ====== Candidate entity tranking runs ======
# CMNS
python -m nordlys.erd.baselines.commonness -c 0.1 -data yeslq-erd
python -m nordlys.erd.baselines.commonness -c 0.1 -data erd

# MLM
python -m nordlys.erd.cer.cer -data ysqle-erd -mlm
python -m nordlys.erd.cer.cer -data erd -mlm

# MLMcg
python -m nordlys.erd.cer.cer -data ysqle-erd -mlm -cmn
python -m nordlys.erd.cer.cer -data erd -mlm -cmn

# LTR
python -m nordlys.erd.groundtruth.gt -gt -data ysqle-erd
python -m nordlys.erd.ml.train_set -cer -cvs -c 0.1 -data ysqle-erd
python -m nordlys.erd.cer.cer -ltr -cv -genfolds -f 5 -c 0.1 -tree 1000 -maxfeat 3 -in ./output/eval/ysqle-erd-cerCV-c0.1.json

python -m nordlys.erd.ml.train_set -cer -ts -c 0.1 -data ysqle-erd
python -m nordlys.erd.cer.cer -ltr -c 0.1 -tree 1000 -maxfeat 3  -train -in ./output/res/ysqle-erd-cerTrain-c0.1.json
python -m nordlys.erd.cer.cer -ltr -rank -c 0.1 -data erd -model output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3.model


# ====== Disambiguation runs ======
# MLM-Greedy

python -m nordlys.erd.isf.isf -in ./output/eval/erd-c0.1-mlm-cmn-0.2-0.0-0.8.json  -greedy -th 20
python -m nordlys.erd.app.erd_app -data erd -c 0.1 -cmn -w 0.2,0.0,0.8 -greedy -th 20 # For measuring time

#LTR-Greedy
python -m nordlys.erd.isf.isf -in ./output/eval/ysqle-erd-cerCV-c0.1-5f-ltr-t1000-m3.json -greedy -th 0.3
python -m nordlys.erd.app.erd_app -data ysqle-erd -c 0.1 -cm ./output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3.model -greedy -th 0.3  # For measuring time

python -m nordlys.erd.isf.isf -in ./output/eval/erd-c0.1-ltr-t1000-m3.json  -greedy -th 0.3
python -m nordlys.erd.app.erd_app -data erd -c 0.1 -cm ./output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3.model -greedy -th 0.3 # For measuring time

# MLM-LTR
python -m nordlys.erd.ml.train_set -isf -cvs -k 5 -in ./output/eval/ysqle-erd-c0.1-mlm-cmn-0.2-0.0-0.8.json
python -m nordlys.erd.isf.isf -cv -genfolds -f 5 -tree 1000 -maxfeat 3 -in ./output/eval/ysqle-erd-c0.1-mlm-cmn-0.2-0.0-0.8-isfCV-k5.json

python -m nordlys.erd.ml.train_set -cer -ts -c 0.1 -data ysqle-erd -nof
python -m nordlys.erd.cer.cer -mlm -cmn -rank -c 0.1 -w 0.2,0.0,0.8 -in ./output/res/ysqle-erd-cerTrain-c0.1-nof.json
python -m nordlys.erd.ml.train_set -isf -ts -k 5 -data ysqle-erd -in ./output/res/ysqle-erd-cerTrain-c0.1-nof-mlm-cmn-0.2-0.0-0.8.json
python -m nordlys.erd.isf.isf -train -tree 1000 -maxfeat 3 -in ./output/res/ysqle-erd-cerTrain-c0.1-nof-mlm-cmn-0.2-0.0-0.8-isfTrain-k5.json
python -m nordlys.erd.app.erd_app -data erd -cmn -c 0.1 -k 5 -w 0.2,0.0,0.8 -im output/res/ysqle-erd-cerTrain-c0.1-nof-mlm-cmn-0.2-0.0-0.8-isfTrain-k5-t1000-m3.model

# LTR-LTR
python -m nordlys.erd.ml.train_set -cer -cvs -c 0.1 -data ysqle-erd
python -m nordlys.erd.ml.train_set -isf -cvs -k 5 -nof -in ./output/eval/ysqle-erd-cerCV-c0.1-5f-ltr-t1000-m3.json
python -m nordlys.erd.ml.train_set -isf -af -in ./output/eval/ysqle-erd-cerCV-c0.1-5f-ltr-t1000-m3-isfCV-k5-nof.json
python -m nordlys.erd.isf.isf -cv -genfolds -f 5 -tree 1000 -maxfeat 3 -in ./output/eval/ysqle-erd-cerCV-c0.1-5f-ltr-t1000-m3-isfCV-k5.json
python -m nordlys.erd.app.erd_app -data ysqle-erd -c 0.1 -k 5 -cm output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3.model -im output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3-isfTrain-k5-t1000-m3.model

python -m nordlys.erd.cer.cer -ltr -c 0.1 -rank -in ./output/res/ysqle-erd-cerTrain-c0.1.json -model ./output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3.model
python -m nordlys.erd.ml.train_set -isf -ts -k 5 -data ysqle-erd -nof -in ./output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3.json
python -m nordlys.erd.ml.train_set -isf -af -in ./output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3-isfTrain-k5-nof.json
python -m nordlys.erd.isf.isf -train -tree 1000 -maxfeat 3 -in output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3-isfTrain-k5.json
python -m nordlys.erd.app.erd_app -data erd -c 0.1 -k 5 -cm ./output/res/ysqle-erd-cerTrain-c0.1-ltr-t1000-m3.model -im output/res/ysqle-erd-cerTrain-c0.1-facc-ltr-t1000-m3-isfTrain-k5-t1000-m3.model