#!/usr/bin/env bash

# example of usage from this folder
# bash run-tpf.sh 4 ../../output/tpf/ "bsbm10,bsbm100,bsbm1k" "0,1000"

CUR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# trap ctrl-c and call ctrl_c()
trap ctrl_c INT

function ctrl_c() {
        echo "Killing..."
        exit 1
}

# require Nodejs in order to run the script
command -v python3 >/dev/null 2>&1 || { echo >&2 "Python3 required for executing queries. Aborting."; exit 1; }

RUNS=$1
OUTPUT=$2
DATASETS=()
while read -rd,; do DATASETS+=("$REPLY"); done <<<"$3,";
BUFFER_SIZE=()
while read -rd,; do BUFFER_SIZE+=("$REPLY"); done <<<"$4,";

JAR="$CUR/../../build/libs/sage-sparql-void-fat-1.0.jar"

if [ "$#" -ne 4 ]; then
  echo "Illegal number of parameters."
  echo "Usage: bash run-sage.sh <number-of-runs> <output-folder> \"<comma-seperated-list-of-datasets>\" \"<comma-seperated-list-of-buffer-size>\""
  exit
fi

mkdir -p $OUTPUT

for dataset in "${!DATASETS[@]}"
do
    for buffer in "${!BUFFER_SIZE[@]}"
    do
        for i in $(seq 1 1 $RUNS)
        do
            echo "#### (${DATASETS[$dataset]}) Running run $i... into $OUTPUT ####"
            bash $CUR/execute-sage.sh "$CUR/../../data/queries/queries-wo-construct.txt" "$OUTPUT/run-$i-${DATASETS[$dataset]}-b-${BUFFER_SIZE[$buffer]}/" "http://localhost:7120/sparql/${DATASETS[$dataset]}" $JAR ${BUFFER_SIZE[$buffer]}
        done
    done
done


for dataset in "${!DATASETS[@]}"
do
    for buffer in "${!BUFFER_SIZE[@]}"
    do
        python3 $CUR/average.py -f $OUTPUT/run-*-${DATASETS[$dataset]}-b-${BUFFER_SIZE[$buffer]}/result.csv -o "$OUTPUT/average-${DATASETS[$dataset]}-b-${BUFFER_SIZE[$buffer]}.csv"
    done
done