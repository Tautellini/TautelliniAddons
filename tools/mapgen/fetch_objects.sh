#!/usr/bin/env bash
# Extract the WMO roots, WMO groups and M2 props placed on the given maps, retrying CDN timeouts.
# Usage: fetch_objects.sh <data_dir> <map>...   (needs the terrain tiles, see fetch_terrain.sh)
# TACTTool runs from <data_dir>/objwork so its download cache does not collide with a terrain fetch running at the same time.
set -u
data="$1"; shift
tool=/c/dev/tools/TACTTool/TACTTool.exe
here="$(cd "$(dirname "$0")" && pwd)"
cdns="eu.cdn.blizzard.com,us.cdn.blizzard.com,blzddist1-a.akamaihd.net"
cd "$data" || exit 1
work="${WORK:-objwork}"  # separate folders keep parallel runs out of each other's cache
mkdir -p "$work"
for step in roots groups m2; do
    case $step in roots) list=wmo-roots.txt; out=extract/wmo ;; groups) list=wmo-groups.txt; out=extract/wmo ;; m2) list=m2.txt; out=extract/m2 ;; esac
    for pass in 1 2 3 4 5; do
        : > "all-$list"
        for map in "$@"; do
            py -3.13 "$here/objects.py" "$data" "$map" "$step" > /dev/null && cat "$list" >> "all-$list"
        done
        sort -u "all-$list" | grep . > "$list"
        missing=$(grep -c . "$list")
        echo "$step pass $pass: $missing missing"
        [ "$missing" -eq 0 ] && break
        (cd "$work" && "$tool" -p wowf -r eu -d "C:/World of Warcraft" --cdns "$cdns" -m list -i "../$list" -o "../$out" > "../extract-$step.log" 2>&1)
    done
done
