#!/bin/bash

# Reusable die() function
# via http://stackoverflow.com/a/7869048/1406873
die() { echo "$@" 1>&2 ; exit 1; }


./download_depth_charts.sh || die "Error downloading depth charts"

for DIVISION in AE AN AS AW NN NS NE NW
do
    echo "Converting \"$DIVISION.html\" to JSON ..."
    ./depth_chart_to_json.sh "$DIVISION.html" || die "Error converting \"$DIVISION.html\" to JSON"
    echo "Converting \"$DIVISION.html.json\" to CSV ..."
    ./depth_chart_json_to_csv.py "$DIVISION.html.json" || die "Error converting \"$DIVISION.html.json\" to CSV"
    echo "OK."
done

echo "Concatenating CSVs together ..."
echo -n "" > depth_charts.csv
for DIVISION in AE AN AS AW NN NS NE NW
do
    cat "$DIVISION.html.json.csv" >> depth_charts.csv
done
echo "Done."
