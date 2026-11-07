#!/usr/bin/env bash
# With arguments, runs only the mutations whose label contains one of them.
# Breaks one behaviour at a time and confirms the test suite notices. Needs a clean tree for
# the mutated files, and restores each from HEAD afterwards.
cd "$(dirname "$0")/../backend" || exit 2
PY=.venv/Scripts/python.exe
[ -x "$PY" ] || PY=.venv/bin/python

FILTERS=("$@")

mutate_eval() { mutate "$1" "../$2" "$3" "$4"; }

mutate() {
  local label=$1 file=$2 from=$3 to=$4
  if [ "${#FILTERS[@]}" -gt 0 ]; then
    local wanted=0 filter
    for filter in "${FILTERS[@]}"; do [[ "$label" == *"$filter"* ]] && wanted=1; done
    [ "$wanted" -eq 1 ] || return
  fi
  git diff --quiet HEAD -- "$file" || { echo "SKIP $label: $file has local changes"; return; }
  sed -i "s#$from#$to#" "$file"
  if git diff --quiet HEAD -- "$file"; then echo "NOOP $label: pattern did not match"; return; fi
  if timeout 180 "$PY" -m pytest -q -x --no-header -p no:cacheprovider >/dev/null 2>&1; then
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
mutate "self-sourced evidence reaches features" src/ledgerlens/confidence/features.py 'independent = record.evidence_independent' 'independent = True'
mutate "document get ignores organization" src/ledgerlens/db/repositories.py 'Document.id == document_id, Document.organization_id == self.organization_id' 'Document.id == document_id'
mutate "document list ignores organization" src/ledgerlens/db/repositories.py '.where(Document.organization_id == self.organization_id)' ''
mutate "job lookup ignores organization" src/ledgerlens/db/repositories.py 'Job.id == job_id, Document.organization_id == self.organization_id' 'Job.id == job_id'
mutate "roles are not enforced" src/ledgerlens/api/deps.py 'if principal.role not in roles:' 'if False:'
mutate "rate limit never trips" src/ledgerlens/api/deps.py 'if count > limit:' 'if False:'
mutate "jwt signature not verified" src/ledgerlens/core/security.py 'options={"require": \["exp", "sub", "org"\]}' 'options={"verify_signature": False}'
mutate "refresh token not rotated" src/ledgerlens/api/auth.py '    stored.revoked_at = now' '    pass'
mutate "extension not checked" src/ledgerlens/ingest/validate.py 'if PurePosixPath(name).suffix.casefold() not in _EXTENSIONS\[mime\]:' 'if False:'
mutate "size not checked" src/ledgerlens/ingest/validate.py 'if len(data) > max_bytes:' 'if False:'
mutate "filename not cleaned" src/ledgerlens/ingest/validate.py 'base = PureWindowsPath(PurePosixPath(name or "upload").name).name' 'base = name or "upload"'
mutate "log redaction disabled" src/ledgerlens/core/logs.py 'if key.casefold() in SENSITIVE_KEYS:' 'if False:'
mutate "api key stored in clear" src/ledgerlens/api/auth.py 'key_hash=digest(key)' 'key_hash=key[:60]'
mutate_eval "fallback values are scored" evals/scoring.py '    if fell_back:' '    if False:'
mutate_eval "exact match counts empty documents" evals/metrics.py 'tp / present if present else None' '(tp + absent) / (present + absent)'
mutate_eval "rows match by best partial only" evals/metrics.py 'share + (_FULL_MATCH_WEIGHT if all_match else 0.0)' 'share'
