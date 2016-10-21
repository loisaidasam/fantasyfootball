
# Rotoworld

## Depth Charts

Data sourced from [http://www.rotoworld.com/teams/depth-charts/nfl.aspx](http://www.rotoworld.com/teams/depth-charts/nfl.aspx)

To get the latest depth chart data from Rotoworld, simply do this:

```bash
./depth_charts
```

What's happening in the background:

- Download depth charts HTML (using [cURL](https://curl.haxx.se/))
- Convert to JSON (using [pup](https://github.com/ericchiang/pup))
- Convert to CSV (using python)
- Concatenate CSVs into one giant `depth_charts.csv` (plain ol' bash shell)

Example result: [depth_charts.2016-10-21-00-33.csv](https://github.com/loisaidasam/fantasyfootball/blob/master/rotoworld/depth_charts.2016-10-21-00-33.csv)
