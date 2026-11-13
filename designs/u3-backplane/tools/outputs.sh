#!/bin/sh
# Fab files, board-only STEP, mechanical drawing and lane lengths of one generated board.
# usage: tools/outputs.sh <boards dir name> <board name> "<drawing title>"     (run from designs/u3-backplane)
set -e
B=boards/$1/$2.kicad_pcb
python3 tools/drc.py $B
python3 gen/fab.py $B boards/$1/bom_raw.json fab/$1
kicad-cli pcb export step --board-only --force -o fab/$1/$2-board.step $B > /dev/null
python3 tools/lengths.py $B fab/$1/$2-lengths.json
python3 tools/mechdraw.py $B docs/$1_mech.svg "$3" \
  "Underside: all cable connectors, right angle, tallest part 13 mm. Keep 15 mm clear below the board." \
  "Assumed, not measured: room in the Jonsbo N5 top compartment; drive end face about 6.5 mm above the board."
