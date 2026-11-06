#!/usr/bin/env bash
# Extract every terrain tile of the given maps, retrying CDN timeouts until nothing is missing.
# Usage: fetch_terrain.sh <data_dir> <map>...   (run from anywhere, TACTTool's cache lands in <data_dir>/cache)
set -u
data="$1"; shift
tool=/c/dev/tools/TACTTool/TACTTool.exe
here="$(cd "$(dirname "$0")" && pwd)"
cdns="eu.cdn.blizzard.com,us.cdn.blizzard.com,blzddist1-a.akamaihd.net"
cd "$data" || exit 1
for map in "$@"; do
    for pass in 1 2 3 4 5; do
        py -3.13 -I "$here/wdt.py" "extract/$map.wdt" db2/UiMapAssignment.csv all "$map" "tiles-$map.txt" "extract/$map" > /dev/null
        missing=$(grep -c . "tiles-$map.txt")
        echo "$map pass $pass: $missing missing"
        [ "$missing" -eq 0 ] && break
        "$tool" -p wowf -r eu -d "C:/World of Warcraft" --cdns "$cdns" -m list -i "tiles-$map.txt" -o "extract/$map" > "extract-$map.log" 2>&1
    done
done
