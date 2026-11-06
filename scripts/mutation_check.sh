#!/usr/bin/env bash
# Breaks one behaviour at a time and confirms the test suite notices. Needs a clean tree for
# the mutated files, and restores each from HEAD afterwards.
cd "$(dirname "$0")/../backend" || exit 2
PY=.venv/Scripts/python.exe
[ -x "$PY" ] || PY=.venv/bin/python

mutate() {
  local label=$1 file=$2 from=$3 to=$4
  git diff --quiet HEAD -- "$file" || { echo "SKIP $label: $file has local changes"; return; }
  sed -i "s/$from/$to/" "$file"
  if git diff --quiet HEAD -- "$file"; then echo "NOOP $label: pattern did not match"; return; fi
  if "$PY" -m pytest -q -x --no-header >/dev/null 2>&1; then
    echo "SURVIVED $label"
  else
    echo "CAUGHT $label"
  fi
  git checkout -q HEAD -- "$file"
}

mutate "label order ignored" src/ledgerlens/extraction/deterministic.py 'reverse=True' 'reverse=False'
mutate "arithmetic rule always passes" src/ledgerlens/verification/rules.py 'difference <= TOLERANCE' 'True'
mutate "bbox not flipped to top-left" src/ledgerlens/parsing/pdfium.py 'page_height - top, right, page_height - bottom' 'bottom, right, top'
mutate "failed rules add no risk" src/ledgerlens/confidence/risk.py '_FAILED_RULE_RISK = 0.4' '_FAILED_RULE_RISK = 0.0'
mutate "invented native confidence" src/ledgerlens/parsing/pdfium.py 'Token(text="".join(chars), bbox=_union(boxes, page_height))' 'Token(text="".join(chars), bbox=_union(boxes, page_height), confidence=0.99)'
mutate "formula text passes to CSV" src/ledgerlens/export/exporters.py 'return "'"'"'" + value' 'return value'
