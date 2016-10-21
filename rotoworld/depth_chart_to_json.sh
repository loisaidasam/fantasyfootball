#!/bin/bash

if [ -z "$1" ]
then
    echo "Missing input html file";
    exit 1;
fi

cat $1 | pup --plain '#cp1_tblDepthCharts json{}' > "$1.json"
