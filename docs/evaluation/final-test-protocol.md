# Final test protocol (CORD v2 test)

Written and committed on 2026-11-12, before any part of this protocol has read the test split. The commit that adds this file is the protocol commit; its hash is recorded in `docs/progress/PROGRESS.md` and in every result file's `environment.git_commit`. Nothing in this file changes after the test read. No system, prompt, threshold, rule, feature or calibrator changes after the test read. A change would be a new, separately named system, scored on new data, not on this test split.

## What was read before this protocol

- CORD test was read once for S1 in Phase 4 (commit `e66ad1f`). That read was rescored from its saved predictions to metrics 1.1 and 1.1.1 (`evals/results/cord_s1_v1_1.json`, `cord_s1_v1_1_1.json`, predictions sha256 `8b3fccde4d463e2d75c1f0ce007d2b34f256dfe60c5518a943b039cca9ab7e47`). It was also reproduced once from the OCR cache (`evals/results/repro/cord_s1_test_repro.json`). S1's rules (`extraction/deterministic.py`, `extraction/layout.py`) have not changed since that read. Other code on S1's path has: the label proximity check (`e62bdd8`) and system options in `evals/systems.py` (`f2ee2d7`, `3d1d416`). Those changes were meant to leave S1's values unchanged. On validation, S1 predictions written after all three changes (2026-11-07 19:48 UTC, `docs/progress/logs/run-s1-records.log`) have the same sha256 (`d4b2385e…`) as those recorded at `86cb81e`, before them.
- No other system has touched test. The OCR cache holds entries for the 100 test documents, from the S1 read.
- Validation results for every system below were read before this protocol. So was a validation-only run of the ablation code (`evals/results/dev/cord_s5_ablations_validation_v1_1_1.json`, log `docs/progress/logs/run-s5-ablations-validation.log`). That run was a smoke test: none of its numbers selects anything, and all ablations below are fixed here regardless of them.

## Fixed configuration

| Item | Value |
|---|---|
| Model | `llama3.2:3b`, digest `a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72`, Ollama 0.40.15, `OLLAMA_MAX_LOADED_MODELS=1` |
| Prompts | pass A `a-2.2`, pass B `b-2.2` |
| LLM parameters | `temperature` 0, `seed` 20261106, `num_ctx` 2304, `num_predict` 1024 |
| Normalisation | version 1.0, sha256 `aa5cf4994ce5fd1b12b2aaf843fa3568f15bffe515b9cefd4dc1bb200760dee1` |
| Metrics | 1.1.1 (`docs/evaluation.md`) |
| Schema | `cord_receipt` 1.1.0 |
| Test split | `evals/splits/cord_v2/ids.json`, test, n = 100, sha256 `b8535d600517fdcf857f79ba0d27d839ae943afab3f4081761a78f29de562049` |
| Bootstrap | 2,000 resamples, seed 20261106, unit = document |
| S5 calibrator | logistic regression, L2, C = 1.0, fitted on CORD train only; thresholds chosen on validation only, lowest point on a 0.001 grid meeting each target (0.98, 0.99) |
| S5 train scopes | S5-S1: `train_all_p1.0` (S1 on all 800 train documents); S5-S4h: `train_all_p2.2` (S4h on all 800 train documents) |
| Grouped variant | `evals/splits/cord_v2/layout_group_holdout.json`: evaluation groups 6, 7, 9 and 10 |

## Systems and commands, in this order

All commands run from the repository root through `uv run --project backend --no-sync python -m …`. `R` below stands for `evals.runners.run_cord --split test --final`.

1. **S1 (records only).** The S1 test result is the Phase 4 read above; it is not scored again. S5-S1 needs S1's per-field records on test, which were never saved. S1 is rerun once to save them: `R --system S1 --records-rerun --save-records`. S1 is deterministic. The rerun must reproduce predictions sha256 `8b3fccde…` exactly, which the runner checks. If it does not, the runner writes no records. S5-S1 on test is then reported as "not evaluated: S1 records rerun did not reproduce the recorded predictions", and no S1 number is replaced.
2. **S2′:** `R --system S2 --label "S2'" --prompt 2.2 --num-ctx 2304`
3. **S3′:** `R --system S3 --label "S3'" --prompt 2.2 --num-ctx 2304`
4. **S4′:** `R --system S4 --label "S4'" --prompt 2.2 --num-ctx 2304`
5. **S4h:** `R --system S4h --label S4h --prompt 2.2 --num-ctx 2304 --save-records`
6. **S5**, four configurations, each read once:
   - `evals.runners.run_s5 --base s1 --train-scope train_all_p1.0 --final`
   - the same with `--variant grouped`
   - `evals.runners.run_s5 --base s4h --train-scope train_all_p2.2 --final`
   - the same with `--variant grouped`
7. **Ablations:** `evals.runners.run_s5_ablations --final`
8. **Degradation**, for each perturbation in the order `blur-1.5`, `blur-3.0`, `jpeg-30`, `jpeg-10`:
   - `R --system S1 --perturb P`
   - then `R --system S4h --label S4h --prompt 2.2 --num-ctx 2304 --perturb P`
9. **Tables and figures:** `bash scripts/tasks.sh reproduce` (equivalent to `make reproduce`).

S2′, S3′, S4′ and S4h share passes A and B. Replies recorded during step 2 or 4 are replayed by later steps, under the same cache key: model, digest, parameters and the full prompt. This is the same reply reused, not a second test read.

## Metrics reported on test

- **S1 to S4h:** everything in the validation tables. Per header field (total, subtotal, tax): precision, recall, F1 and false fill rate, each with a 95% document-bootstrap interval. Row-level line items: rows correct, predicted and gold, with row F1 [95% CI]. Failed extractions, pass fallbacks, retries, truncated replies and withheld values. Warm LLM and warm total p50 / p95 latency, cold-document load times, lowest free RAM, timing source and power label.
- **S5:** for header units and row units, at each target (0.98, 0.99): threshold, accepted / slots, test automation rate [95% CI], test achieved precision [95% CI] and whether the target was met, reported even when it is not met. Also ECE (10 equal-width bins), Brier score and ROC-AUC on test. Grouped variant: test is reported separately for documents of the unseen evaluation groups and of the calibration groups.

## Ablations (calibrator refits only; no model calls)

Bases S5-S1 and S5-S4h, the "all" variant, both targets, header and row units. Each ablation refits on train, chooses thresholds on validation and is scored once on test. Feature families, by exact feature key (a key also matches a row feature that ends in `_<key>`, such as `amount_rules_passed`):

| Ablation | Removed features |
|---|---|
| `full` (reference) | none; must equal the S5 "all" result |
| `minus_label_proximity` | `label_supported` |
| `minus_ab_agreement` | `agree_pass_a_b`, `cross_pass_available`, `agree_count`, `sources_with_value` |
| `minus_rule_llm_agreement` | `agree_rules_llm`, `agree_pass_a_deterministic`, `agree_count`, `sources_with_value` |
| `minus_ocr_confidence` | `ocr_confidence_mean`, `ocr_confidence_min`, `ocr_confidence_available` |
| `minus_format_validation` | `value_valid`, `rules_passed`, `rules_failed`, `rules_checked` |
| `isotonic` | none; the logistic model's scores are mapped by isotonic regression (`CalibratedClassifierCV`, method isotonic), cross-fitted on train in 5 folds grouped by document (`GroupKFold`) |

- `agree_count` and `sources_with_value` count agreement over all sources, so both agreement ablations remove them.
- Always kept: the independent evidence features (`independent_*`, `llm_evidence_found`, `llm_value_in_evidence`), `value_present`, and the categorical `source`, `s4h_choice` and field name.
- Row units carry only evidence and rule-check features. So for rows, only `minus_format_validation` and `isotonic` can change the model; the other ablations leave the row model identical. That is stated in the table, not hidden.
- Code: `evals/s5.py` (`SIGNAL_FAMILIES`, `Calibrator.fit`) and `evals/runners/run_s5_ablations.py`.

## Degradation study (limited by hardware)

- **Systems:** S1 and S4h only.
- **Images:** the 100 test images, each perturbed by fixed, deterministic transforms (`evals/perturb.py`; the same input always gives the same output, so no random seed is involved):
  - Gaussian blur, radius (standard deviation) 1.5 and 3.0 pixels, saved as PNG;
  - JPEG re-encoding at quality 30 and 10, with 4:2:0 subsampling.
- **Pipeline:** each perturbed copy gets its own OCR cache entry, keyed `<document id>#<perturbation>`. OCR, extraction and scoring are then as in the clean run.
- **Run-time estimate:** made before this protocol (`evals/runners/estimate_runtime.py`, log `docs/progress/logs/run-estimate-runtime.log`). It uses 1,651 llama3.2:3b replies recorded entirely on AC: mean 4.73 s per call and 2.01 calls per document for S4h. The LLM document runs are the clean test (100) plus S4h on 4 degraded variants (400). Expected LLM time is 1.32 hours. The upper bound, if every reply ran to `num_predict` at the median 47.8 tokens/s, is 5.98 hours.
- **Decision:** both are under 6 hours, so the full study above runs, with no reduction.

## Run conditions

- **Pre-flight:**
  - fresh reboot;
  - AC power;
  - Docker stopped;
  - free RAM at least 2 GiB;
  - model warmed with one request;
  - keep-awake on.
  Each is checked and logged in `docs/progress/logs/final-preflight.txt` before step 1.
- **Clean commit:** all steps run in one session from a clean commit, `git status --porcelain` empty. Result files record `git_dirty`.
- **AC only:** the test split runs on AC only. `run_cord` refuses to start off AC, and aborts and writes nothing if AC is lost. Every result carries a power label. Latency is quoted only from results labelled `ac`.
- **Memory aborts:** a run aborts when free RAM falls below 0.4 GiB. The step is then rerun with the same command and settings, resuming from the OCR and reply caches; an aborted attempt writes no result. Every abort is recorded in `evals/results/aborted/` and counted per step in `docs/progress/logs/final-run-metadata.json`.
- **Other failures:** any failure other than a memory abort stops the protocol, and it is reported as it is.

## Output files

- `evals/results/cord_{s2p,s3p,s4p,s4h}_v1_1_1.json`, and `evals/results/repro/cord_s1_test_records_rerun_v1_1_1.json`
- `evals/results/cord_s5_{s1,s1_grouped,s4h,s4h_grouped}_v1_1_1.json`
- `evals/results/cord_s5_ablations_v1_1_1.json`
- `evals/results/degradation/cord_{s1,s4h}_{blur-1.5,blur-3.0,jpeg-30,jpeg-10}_v1_1_1.json`
- `docs/progress/logs/final-preflight.txt`, `docs/progress/logs/final-run.log`, `docs/progress/logs/final-run-metadata.json`
- `evals/results/final/`, generated, never edited:
  - `cord_test_comparison_v1_1_1.{md,json}`: the validation comparison's two tables (single-valued fields; rows, failures and latency, with the Power column), for S1, S2′, S3′, S4′ and S4h;
  - `cord_s5_test_v1_1_1.md`: the S5 validation table's columns, from the test blocks;
  - `cord_s5_ablations_test_v1_1_1.md`: base, ablation, units, target, threshold, test automation [CI], test achieved precision [CI], target met, change in automation against `full`, ROC-AUC, ECE, columns removed;
  - `cord_degradation_test_v1_1_1.md`: system, condition, total, subtotal, tax and row F1 [CI], mean of the four F1, change in mean against clean, failed, truncated, power;
  - `cord_degradation_test_v1_1_1.png`: mean of the four F1 by condition, for S1 and S4h.
