# Review 4 report (with notes A, B and C)

Report as of commit 911211f, 2026-11-08. Nothing is pushed. No commit has an AI trailer: `git log 9007502^..HEAD --format=%B | grep -ciE "co-authored|generated with|claude"` gives 0.

## 1. Status

| Item | Status | Evidence |
|---|---|---|
| Memory discrepancy measured and explained | VERIFIED | docs/progress/ENVIRONMENT.md, "Memory measurement"; evals/results/dev/memory_measurement.json |
| qwen3:4b thinking-off | VERIFIED | commit dffefb0, unit tests |
| qwen3:4b comparison, pre-registered | VERIFIED (pre-registration) | commit 33eb171 |
| qwen3:4b comparison, run | BLOCKED | Two memory aborts during token measurement, before any quality result. Not adopted (ADR-0012) |
| Adopted model | VERIFIED | llama3.2:3b (digest a80c4f17acd5) |
| S5-S1 pre-registered next to S5-S4h | VERIFIED | commit 33eb171 |
| S1 on all 800 train documents | VERIFIED | evals/results/dev/prompt_round/cord_s1_train_all_p1.0_v1_1_1.json |
| S4h llama3.2:3b on all 800 train documents | VERIFIED | evals/results/dev/prompt_round/cord_s4h_train_all_p2.2_v1_1_1.json; 10 attempts, 9 memory aborts |
| S5-S1 on validation | VERIFIED | evals/results/dev/cord_s5_validation_comparison_v1_1_1.md |
| S5-S4h on validation | VERIFIED | same file; docs/progress/logs/run-s5-s4h-{all,grouped}.log |
| 48 s against 10 s per document diagnosed | VERIFIED | ENVIRONMENT.md; docs/progress/logs/s4h-train-all-segments.json, s4h-train-all-monitor.txt |
| Keep-awake released after the run | VERIFIED | "keep-awake released: stopped 1 process(es)" in docs/progress/logs/run-s4h-train-all-direct.log and the monitor log |
| Power state on every timed run; audit and labels | VERIFIED | evals/power.py, evals/runners/audit_power.py, docs/progress/logs/power-audit.json; Power column in every results table |
| Test split runs on AC only | IMPLEMENTED BUT UNVERIFIED | Guard in evals/runners/run_cord.py. It was not exercised, because reading test is not allowed yet |
| ADR-0012 wording | VERIFIED | docs/adr/0012-qwen3-not-adopted.md |
| README S5 wording | VERIFIED | README.md, "S5: when a value can skip human review" |
| Webhooks: HMAC-signed, with retries | VERIFIED | backend/tests/api/test_webhooks.py (10 tests) |
| Phase 6 frontend | VERIFIED | 36 Vitest tests pass (3 files) |
| Playwright upload, review, export | VERIFIED | Local dev stack: docs/progress/logs/run-e2e-local.log. Compose stack: docs/progress/logs/run-e2e-docker.log |
| Phase 9 Dockerfiles; worker in Compose; up to healthy | VERIFIED | docs/progress/logs/run-docker-compose-up.log |
| Final S1-S5 test read | NOT STARTED | Last step, on AC, from a clean commit |
| Backend test suite | VERIFIED | 412 passed (pytest -q, 2026-11-08) |

## 2. Memory explanation

The two free-RAM measures (psutil available, and Win32 FreePhysicalMemory) agree within 0.02 GiB, so the discrepancy is not a difference in definition. In the dedicated measurement, llama3.2:3b at num_ctx 2304 costs about 0.6 to 0.9 GiB of system RAM (runner RSS 0.70 GiB idle, 0.91 GiB during a document), with its weights in VRAM. Over the whole 800-document S4h run, the result file records a peak runner RSS of 3.919 GiB. That is higher than in the dedicated measurement; I have not explained the difference. The low readings came from higher contexts, from page images loaded in the evaluation process (removed, saving about 1 GiB), or from OCR running at the same time. Two S4' aborts happened in the lean configuration and stay unexplained; they came from something outside the run. The 9 aborts in the 800-document S4h run were all recorded on AC. Free RAM during that run ranged from 0.261 to 6.148 GiB, and pagefile use from 1,136 to 2,121 MB. Details: ENVIRONMENT.md.

## 3. qwen3:4b: pre-registration and comparison

Pre-registration: commit 33eb171. Adoption needed all three:

1. mean F1 to improve by at least 0.05;
2. warm p95 at most twice llama's;
3. at most one memory abort.

| Model | Mean F1 (train subset, S4h) | Warm LLM p95 s | Memory aborts | Power |
|---|---|---|---|---|
| llama3.2:3b (baseline, recorded as measured, not rerun) | 0.578 | 19.73 | 3 | ac |
| qwen3:4b | not evaluated | not evaluated | 2, during token measurement, before the comparison | battery at the time of both aborts (about 21:05 UTC, 2026-11-07) |

Outcome: qwen3:4b was not adopted, for insufficient system RAM on this machine (memory aborts during setup). No quality judgement was made (ADR-0012). The aborts happened while on battery, but they were memory aborts, not slowdowns, so the decision stands. The 800-document run used **llama3.2:3b**.

## 4. S5 on validation, S5-S1 and S5-S4h

Calibrators were fitted on CORD train only. Thresholds were chosen on validation, so the rates are in-sample for the thresholds. Test was not read. Full table: evals/results/dev/cord_s5_validation_comparison_v1_1_1.md.

| System | Variant | Units | Target | Threshold | Accepted / slots | Automation [95% CI] | Precision [95% CI] | ECE | Brier | AUC |
|---|---|---|---|---|---|---|---|---|---|---|
| S5-S1 | all | header | 0.98 | 0.869 | 71 / 300 | 0.237 [0.170, 0.310] | 0.986 [0.949, 1.000] | 0.027 | 0.078 | 0.825 |
| S5-S1 | all | header | 0.99 | 0.878 | 70 / 300 | 0.233 [0.163, 0.303] | 1.000 | 0.027 | 0.078 | 0.825 |
| S5-S1 | all | row | 0.98, 0.99 | 0.763 | 3 / 230 | 0.013 [0.000, 0.030] | 1.000 | 0.060 | 0.126 | 0.858 |
| S5-S1 | grouped | header | 0.98, 0.99 | 0.891 | 53 / 222 | 0.239 [0.158, 0.329] | 1.000 | 0.035 | 0.076 | 0.831 |
| S5-S1 | grouped | row | 0.98, 0.99 | 0.738 | 3 / 167 | 0.018 [0.000, 0.040] | 1.000 | 0.038 | 0.128 | 0.853 |
| S5-S4h | all | header | 0.98 | 0.966 | 59 / 300 | 0.197 [0.147, 0.247] | 0.983 [0.942, 1.000] | 0.056 | 0.083 | 0.942 |
| S5-S4h | all | header | 0.99 | 0.969 | 47 / 300 | 0.157 [0.107, 0.207] | 1.000 | 0.056 | 0.083 | 0.942 |
| S5-S4h | all | row | 0.98, 0.99 | 0.826 | 1 / 354 | 0.003 [0.000, 0.009] | 1.000 | 0.049 | 0.081 | 0.925 |
| S5-S4h | grouped | header | 0.98, 0.99 | 0.968 | 38 / 222 | 0.171 [0.113, 0.230] | 1.000 | 0.060 | 0.071 | 0.955 |
| S5-S4h | grouped | row | 0.98, 0.99 | 0.809 | 1 / 272 | 0.004 [0.000, 0.013] | 1.000 | 0.056 | 0.090 | 0.907 |

Reading: S5-S4h's scores separate right from wrong values better (AUC 0.94 against 0.83), but S5-S1 automates more header fields at the same precision target. A likely reason, not tested: S1 leaves a field empty rather than guess (false fill 0.000), so more of its filled values are right. Line items are effectively routed to human review under both base systems. The README states this, with header and row automation side by side.

S4h on all 800 train documents (the S5-S4h training input), F1: total 0.791, subtotal 0.694, tax 0.500, rows 0.253. 1 failed extraction, 21 retries, 31 truncated replies. Its latency is labelled battery-affected (103 of 2,421 timings on battery) and is not used for any claim.

## 5. The 48 s against 10 s diagnosis

The latency is split at every power change in the Windows Kernel-Power log (event 105) and never pooled:

| Segment (UTC) | Power | LLM calls | p50 s | p95 s | Tokens/s median |
|---|---|---|---|---|---|
| 11-07 21:11 to 21:40 (before the critical-battery sleep) | battery | 51 | 29.1 | 55.53 | 6.7 |
| 11-08 05:44 to 06:31:24 | AC | 505 | 3.95 | 11.3 | 48.1 |
| 11-08 06:31:24 to 06:49:24 | battery | 52 | 14.86 | 28.34 | 13.6 |
| 11-08 06:49:24 to the end (07:56:52) | AC | 744 | 4.04 | 8.69 | 47.7 |

`ollama ps` showed `100% GPU` in all 54 monitor snapshots where the model was loaded, so CPU offload is ruled out. On battery, GPU clock and power had a median of 277 MHz and 5.6 W, against 1,432 MHz and 43.1 W on AC. Pagefile use stayed between 1.1 and 2.1 GB. Explanation: the slow segments ran on battery.

Correction to my earlier note: the "post-restart on AC" row I gave before (308 calls) included 52 battery calls from the 06:31 to 06:49 interval, which only the power audit found. ENVIRONMENT.md records the correction.

## 6. Power audit

Every timed result now has a `power` block. Timings are dated by their cache file's modification time, or by the run log's window for synthetic and one-off runs. A sanity check found that all 103 battery-dated cache files belong to the S4h train_all run, and that all 1,000 OCR cache files were recorded on AC.

- battery-affected: evals/results/dev/prompt_round/cord_s4h_train_all_p2.2_v1_1_1.json only.
- ac: every other timed result. That covers all validation tables, the prompt round, the train-subset llama baseline, the S1 test repro, synthetic S2', the memory measurement and the LLM smoke test.

The README quotes no latency figures. For the final test read, run_cord refuses to start unless Windows reports AC power, and it aborts if AC is lost during the run. Each test result records its power label.

## 7. Product track

- Frontend: 36 Vitest tests pass (3 files); `npm run build` passes.
- Playwright upload → review → export: 1 passed on the local dev stack (10.2 s), and 1 passed against the Docker Compose stack (8.5 s; docs/progress/logs/run-e2e-docker.log).
- Webhooks: HMAC-SHA256 over "timestamp.body", https-only URLs with no private addresses, delivered on RQ with retries; 10 API tests.
- Docker: `docker compose -f infra/docker-compose.yml --env-file .env up -d --build --wait`. All five services reported healthy:

```
ledgerlens-api-1 Up About a minute (healthy) 127.0.0.1:8000->8000/tcp
ledgerlens-postgres-1 Up 33 minutes (healthy) 127.0.0.1:5433->5432/tcp
ledgerlens-redis-1 Up 33 minutes (healthy) 127.0.0.1:6380->6379/tcp
ledgerlens-web-1 Up 12 seconds (healthy) 127.0.0.1:8081->8080/tcp
ledgerlens-worker-1 Up About a minute (healthy) 8000/tcp
api /health/ready: 200 {"status":"ready","checks":{"database":true,"redis":true,"storage":true,"worker":true}}
web /: 200
web /api/health/ready (proxied): 200
```

The first two `up` attempts failed. An unrelated `httpd` process (PID 5752) holds 0.0.0.0:8080 on this machine; it is not part of this project and I did not stop it. The web host port is now `LEDGERLENS_WEB_PORT`, default 8080, and this run used 8081. The Docker worker runs in rules mode by default; the LLM mode against host Ollama was not exercised in Docker.

## 8. Blockers and open items

1. Memory: the 800-document run needed 10 attempts, and the replay cache made them safe. Free RAM on this 16 GB machine is the binding constraint for any larger model.
2. qwen3:4b was not evaluated (RAM). A comparison needs a machine with more RAM.
3. The final S1-S5 test read waits for your go-ahead. It will run on AC, from a clean commit, once per configuration.
4. CI on GitHub stays unverified until you create a remote. Nothing has been pushed.
5. Phase 8 hardening, ablations and degradation, and the portfolio write-up are not started.

## 9. The four requested files, verbatim

Each file below is copied by script, byte for byte, from the commit named at the top.

| File | sha256 |
|---|---|
| evals/results/dev/prompt_round/prompt_round.md | 1bd82e17db5d25fd600476fe6289b3b34c485fa7b849ab0e6843d996c8aef883 |
| evals/results/dev/prompt_round/prompt_round.json | 6d3aa444a5804f246c2afbd2b6d6526c9d4750046c5f8ee14e3b409b35199722 |
| evals/results/dev/cord_validation_comparison_v1_1_1.md | d55f4615dd797f489a8cd954f189a44ea3a14f8c87b009256321bdd5c8268122 |
| evals/results/dev/cord_validation_comparison_v1_1_1.json | ccf0ddc1f41a4ecf12daaafe6741b69d3b4fd18dd0959785af940a8cd76ea4d6 |

### evals/results/dev/prompt_round/prompt_round.md

````markdown
# Prompt round 2: S2 on the 100-document CORD train subset (metrics 1.1.1)

Generated by `evals/runners/make_prompt_round_table.py`. Do not edit by hand. Validation was not read for this choice.

| Prompt | Role | Total F1 | Subtotal F1 | Tax F1 | Row F1 | Mean | Failed | Truncated | num_ctx | Warm LLM p50 / p95 s | Power |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.0 | reference | 0.785 | 0.549 | 0.429 | 0.034 | 0.449 | 1 | 3 | 4096 | 2.57 / 10.21 | ac |
| 2.0 | candidate | 0.614 | 0.642 | 0.530 | 0.057 | 0.461 | 1 | 2 | 2048 | 4.01 / 14.31 | ac |
| 2.1 | candidate | 0.720 | 0.608 | 0.532 | 0.048 | 0.477 | 1 | 3 | 2048 | 5.15 / 17.36 | ac |
| 2.2 | **chosen** | 0.737 | 0.454 | 0.545 | 0.246 | 0.495 | 0 | 2 | 2304 | 3.46 / 8.35 | ac |

Chosen prompt: **2.2**, by the highest mean of the four F1 values among the candidates, ties to the shorter prompt.
````

### evals/results/dev/prompt_round/prompt_round.json

````json
{
  "scores": {
    "1.0": {
      "total_amount": 0.7853403141361257,
      "subtotal": 0.5487804878048781,
      "tax_amount": 0.42857142857142855,
      "rows": 0.03443328550932568,
      "mean": 0.4492813790054395
    },
    "2.0": {
      "total_amount": 0.6143790849673203,
      "subtotal": 0.6415094339622641,
      "tax_amount": 0.5301204819277109,
      "rows": 0.057210965435041714,
      "mean": 0.46080499157308424
    },
    "2.1": {
      "total_amount": 0.7195121951219512,
      "subtotal": 0.6078431372549019,
      "tax_amount": 0.5316455696202531,
      "rows": 0.04847207586933614,
      "mean": 0.4768682444666106
    },
    "2.2": {
      "total_amount": 0.7368421052631579,
      "subtotal": 0.4536082474226804,
      "tax_amount": 0.5454545454545454,
      "rows": 0.24570673712021135,
      "mean": 0.49540290881514876
    }
  },
  "final_prompt": "2.2"
}
````

### evals/results/dev/cord_validation_comparison_v1_1_1.md

````markdown
# CORD validation, all systems (metrics 1.1.1, development only)

Generated by `evals/runners/make_validation_comparison.py`. Do not edit by hand. Primed systems use the round-two prompt chosen on the train subset; S4h was pre-registered before any result. Each was read once on validation.

## Single-valued fields: precision / recall / F1 [95% CI], false fill rate

| System | Prompt | Field | Precision | Recall | F1 | False fill |
|---|---|---|---|---|---|---|
| S1 | none | Total | 0.867 [0.793, 0.934] | 0.796 [0.714, 0.876] | 0.830 [0.755, 0.899] | 0.000 [0.000, 0.000] |
| S1 | none | Subtotal | 0.960 [0.896, 1.000] | 0.716 [0.606, 0.819] | 0.821 [0.734, 0.893] | 0.000 [0.000, 0.000] |
| S1 | none | Tax | 0.878 [0.771, 0.972] | 0.766 [0.644, 0.886] | 0.818 [0.711, 0.916] | 0.000 [0.000, 0.000] |
| S2 | a-1.0 | Total | 0.823 [0.742, 0.898] | 0.806 [0.724, 0.883] | 0.814 [0.736, 0.890] | 1.000 [1.000, 1.000] |
| S2 | a-1.0 | Subtotal | 0.571 [0.473, 0.674] | 0.776 [0.671, 0.873] | 0.658 [0.562, 0.753] | 0.788 [0.643, 0.920] |
| S2 | a-1.0 | Tax | 0.351 [0.246, 0.461] | 0.574 [0.431, 0.721] | 0.435 [0.319, 0.548] | 0.717 [0.596, 0.833] |
| S3 | a-1.0 | Total | 0.823 [0.742, 0.898] | 0.806 [0.724, 0.883] | 0.814 [0.736, 0.890] | 1.000 [1.000, 1.000] |
| S3 | a-1.0 | Subtotal | 0.571 [0.473, 0.674] | 0.776 [0.671, 0.873] | 0.658 [0.562, 0.753] | 0.788 [0.643, 0.920] |
| S3 | a-1.0 | Tax | 0.370 [0.260, 0.485] | 0.574 [0.431, 0.721] | 0.450 [0.330, 0.565] | 0.642 [0.517, 0.771] |
| S4 | a-1.0 | Total | 0.830 [0.750, 0.900] | 0.847 [0.773, 0.918] | 0.838 [0.761, 0.909] | 1.000 [1.000, 1.000] |
| S4 | a-1.0 | Subtotal | 0.609 [0.511, 0.707] | 0.836 [0.742, 0.919] | 0.704 [0.612, 0.790] | 0.788 [0.643, 0.920] |
| S4 | a-1.0 | Tax | 0.400 [0.291, 0.513] | 0.681 [0.543, 0.816] | 0.504 [0.386, 0.618] | 0.660 [0.532, 0.790] |
| S2' | a-2.2 | Total | 0.734 [0.642, 0.819] | 0.704 [0.610, 0.794] | 0.719 [0.628, 0.802] | 1.000 [1.000, 1.000] |
| S2' | a-2.2 | Subtotal | 0.841 [0.721, 0.941] | 0.552 [0.427, 0.672] | 0.667 [0.547, 0.770] | 0.091 [0.000, 0.200] |
| S2' | a-2.2 | Tax | 0.493 [0.377, 0.608] | 0.766 [0.641, 0.884] | 0.600 [0.483, 0.704] | 0.566 [0.429, 0.702] |
| S3' | a-2.2 | Total | 0.793 [0.701, 0.875] | 0.704 [0.610, 0.794] | 0.746 [0.656, 0.825] | 1.000 [1.000, 1.000] |
| S3' | a-2.2 | Subtotal | 0.974 [0.914, 1.000] | 0.552 [0.427, 0.672] | 0.705 [0.589, 0.800] | 0.000 [0.000, 0.000] |
| S3' | a-2.2 | Tax | 0.554 [0.429, 0.677] | 0.766 [0.641, 0.884] | 0.643 [0.524, 0.748] | 0.434 [0.306, 0.571] |
| S4' | a-2.2 | Total | 0.830 [0.747, 0.904] | 0.796 [0.714, 0.878] | 0.812 [0.734, 0.888] | 1.000 [1.000, 1.000] |
| S4' | a-2.2 | Subtotal | 0.640 [0.541, 0.739] | 0.851 [0.761, 0.930] | 0.731 [0.639, 0.812] | 0.788 [0.636, 0.925] |
| S4' | a-2.2 | Tax | 0.458 [0.346, 0.568] | 0.809 [0.687, 0.911] | 0.585 [0.472, 0.691] | 0.717 [0.596, 0.836] |
| S4h | a-2.2 | Total | 0.832 [0.750, 0.905] | 0.806 [0.727, 0.888] | 0.819 [0.741, 0.893] | 1.000 [1.000, 1.000] |
| S4h | a-2.2 | Subtotal | 0.637 [0.538, 0.733] | 0.866 [0.778, 0.940] | 0.734 [0.645, 0.814] | 0.818 [0.684, 0.941] |
| S4h | a-2.2 | Tax | 0.447 [0.337, 0.557] | 0.809 [0.687, 0.911] | 0.576 [0.465, 0.681] | 0.755 [0.638, 0.868] |

## Rows, failures and latency

| System | Rows correct / predicted / gold | Row F1 [95% CI] | Failed | Pass fallbacks | Retries | Truncated | Withheld | Warm LLM p50 / p95 s | Warm total p50 / p95 s | Cold docs: load s; cold LLM s excl. load | Lowest free RAM GiB | Timings | Power |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 85 / 230 / 221 | 0.377 [0.296, 0.456] | 0 | 0 | 0 | 0 | 0 | none (no model) | 2.55 / 4.71 | none | 1.622 | measured in this run | ac |
| S2 | 17 / 361 / 221 | 0.058 [0.022, 0.110] | 0 | 0 | 0 | 0 | 0 | 2.37 / 7.31 | 5.26 / 9.91 | 69.5; 58.1; 7.3; 4.3 | 0.265 | recorded when the call was first made | ac |
| S3 | 16 / 357 / 221 | 0.055 [0.021, 0.102] | 0 | 0 | 0 | 0 | 44 | 2.37 / 7.31 | 5.26 / 9.91 | 69.5; 58.1; 7.3; 4.3 | 1.647 | recorded when the call was first made | ac |
| S4 | 16 / 357 / 221 | 0.055 [0.021, 0.102] | 0 | 0 | 1 | 1 | 37 | 4.73 / 11.20 | 7.43 / 14.79 | 69.6; 63.5; 7.4; 8.1 | 0.253 | recorded when the call was first made | ac |
| S2' | 65 / 422 / 221 | 0.202 [0.140, 0.267] | 0 | 0 | 0 | 0 | 0 | 3.42 / 6.61 | 6.32 / 10.27 | 4.8; 5.7 | 2.994 | mixed: 99 calls measured in this run, 1 recorded earlier (an aborted run or an earlier system) and replayed | ac |
| S3' | 65 / 410 / 221 | 0.206 [0.142, 0.271] | 0 | 0 | 0 | 0 | 94 | 3.42 / 6.61 | 6.25 / 10.17 | 4.8; 5.7 | 3.31 | recorded when the call was first made | ac |
| S4' | 65 / 412 / 221 | 0.205 [0.142, 0.271] | 0 | 0 | 1 | 1 | 109 | 7.68 / 14.05 | 10.43 / 17.93 | 4.8; 11.9; 6.9; 8.8; 6.7; 9.2 | 3.289 | mixed: 14 calls measured in this run, 187 recorded earlier (an aborted run or an earlier system) and replayed | ac |
| S4h | 84 / 354 / 221 | 0.292 [0.219, 0.367] | 0 | 0 | 1 | 1 | 0 | 7.68 / 14.05 | 10.43 / 17.94 | 4.8; 11.9; 6.9; 8.8; 6.7; 9.2 | 3.285 | recorded when the call was first made | ac |
````

### evals/results/dev/cord_validation_comparison_v1_1_1.json

````json
{
  "metrics_version": "1.1.1",
  "split": "validation",
  "note": "Development only. Test has not been read for these systems.",
  "systems": [
    {
      "system": "S1",
      "source": "evals/results/dev/cord_s1_validation_v1_1_1.json",
      "model": null,
      "prompt": null,
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.8666666666666667,
          "precision_ci95": [
            0.7934782608695652,
            0.9340659340659341
          ],
          "recall": 0.7959183673469388,
          "recall_ci95": [
            0.7142477203647417,
            0.8762886597938144
          ],
          "f1": 0.8297872340425532,
          "f1_ci95": [
            0.7553191489361702,
            0.8994708994708994
          ],
          "false_fill_rate": 0.0,
          "false_fill_rate_ci95": [
            0.0,
            0.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.96,
          "precision_ci95": [
            0.8958059210526316,
            1.0
          ],
          "recall": 0.7164179104477612,
          "recall_ci95": [
            0.605572322825844,
            0.8194807213930346
          ],
          "f1": 0.8205128205128205,
          "f1_ci95": [
            0.7339449541284404,
            0.892569362455726
          ],
          "false_fill_rate": 0.0,
          "false_fill_rate_ci95": [
            0.0,
            0.0
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.8780487804878049,
          "precision_ci95": [
            0.7714136904761905,
            0.9722409909909909
          ],
          "recall": 0.7659574468085106,
          "recall_ci95": [
            0.6444047619047619,
            0.8863636363636364
          ],
          "f1": 0.8181818181818182,
          "f1_ci95": [
            0.7110964912280702,
            0.9156626506024096
          ],
          "false_fill_rate": 0.0,
          "false_fill_rate_ci95": [
            0.0,
            0.0
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 85,
        "rows_predicted": 230,
        "rows_gold": 221,
        "precision": 0.3695652173913043,
        "recall": 0.38461538461538464,
        "f1": 0.376940133037694,
        "documents_all_rows_correct": 0.21,
        "precision_ci95": [
          0.2863631357629155,
          0.4555677655677655
        ],
        "recall_ci95": [
          0.3009145148669797,
          0.47107636681500314
        ],
        "f1_ci95": [
          0.2958250802997859,
          0.4561682536360781
        ],
        "documents_all_rows_correct_ci95": [
          0.13975000000000004,
          0.29
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 0,
        "truncated_replies": 0
      },
      "values_withheld": 0,
      "latency_seconds": {
        "source": "measured in this run",
        "warm_llm": null,
        "warm_total": {
          "n": 100,
          "p50": 2.5509770500066224,
          "p95": 4.706929900008253
        },
        "cold": {
          "documents": 0,
          "model_load_seconds": [],
          "cold_llm_seconds_excluding_load": []
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 100,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 1.622
    },
    {
      "system": "S2",
      "source": "evals/results/dev/cord_s2_validation_v1_1_1.json",
      "model": "llama3.2:3b",
      "prompt": "a-1.0",
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.8229166666666666,
          "precision_ci95": [
            0.7422680412371134,
            0.8979591836734694
          ],
          "recall": 0.8061224489795918,
          "recall_ci95": [
            0.7244897959183674,
            0.8830095184770435
          ],
          "f1": 0.8144329896907216,
          "f1_ci95": [
            0.7357512953367875,
            0.8900808398665327
          ],
          "false_fill_rate": 1.0,
          "false_fill_rate_ci95": [
            1.0,
            1.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.5714285714285714,
          "precision_ci95": [
            0.47251203852327445,
            0.6736899313501143
          ],
          "recall": 0.7761194029850746,
          "recall_ci95": [
            0.6714236790606654,
            0.873015873015873
          ],
          "f1": 0.6582278481012658,
          "f1_ci95": [
            0.5625,
            0.753116402116402
          ],
          "false_fill_rate": 0.7878787878787878,
          "false_fill_rate_ci95": [
            0.6428571428571429,
            0.9200263157894736
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.35064935064935066,
          "precision_ci95": [
            0.246371237458194,
            0.4605263157894737
          ],
          "recall": 0.574468085106383,
          "recall_ci95": [
            0.4313640973630832,
            0.7209302325581395
          ],
          "f1": 0.43548387096774194,
          "f1_ci95": [
            0.3185840707964602,
            0.5484178773701057
          ],
          "false_fill_rate": 0.7169811320754716,
          "false_fill_rate_ci95": [
            0.5961436170212766,
            0.8333333333333334
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 17,
        "rows_predicted": 361,
        "rows_gold": 221,
        "precision": 0.04709141274238227,
        "recall": 0.07692307692307693,
        "f1": 0.058419243986254296,
        "documents_all_rows_correct": 0.01,
        "precision_ci95": [
          0.017906849003712404,
          0.08943500634428307
        ],
        "recall_ci95": [
          0.02898401006108516,
          0.14095779220779192
        ],
        "f1_ci95": [
          0.022421645066349975,
          0.10978488362943958
        ],
        "documents_all_rows_correct_ci95": [
          0.0,
          0.03
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 0,
        "truncated_replies": 0
      },
      "values_withheld": 0,
      "latency_seconds": {
        "source": "recorded when the call was first made",
        "warm_llm": {
          "n": 98,
          "p50": 2.3719832000066026,
          "p95": 7.313741515011507
        },
        "warm_total": {
          "n": 98,
          "p50": 5.258191500016075,
          "p95": 9.909243390033046
        },
        "cold": {
          "documents": 2,
          "model_load_seconds": [
            69.5487653,
            7.331563
          ],
          "cold_llm_seconds_excluding_load": [
            58.07148729999791,
            4.314486800008768
          ]
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 200,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 0.265
    },
    {
      "system": "S3",
      "source": "evals/results/dev/cord_s3_validation_v1_1_1.json",
      "model": "llama3.2:3b",
      "prompt": "a-1.0",
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.8229166666666666,
          "precision_ci95": [
            0.7422680412371134,
            0.8979591836734694
          ],
          "recall": 0.8061224489795918,
          "recall_ci95": [
            0.7244897959183674,
            0.8830095184770435
          ],
          "f1": 0.8144329896907216,
          "f1_ci95": [
            0.7357512953367875,
            0.8900808398665327
          ],
          "false_fill_rate": 1.0,
          "false_fill_rate_ci95": [
            1.0,
            1.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.5714285714285714,
          "precision_ci95": [
            0.47251203852327445,
            0.6736899313501143
          ],
          "recall": 0.7761194029850746,
          "recall_ci95": [
            0.6714236790606654,
            0.873015873015873
          ],
          "f1": 0.6582278481012658,
          "f1_ci95": [
            0.5625,
            0.753116402116402
          ],
          "false_fill_rate": 0.7878787878787878,
          "false_fill_rate_ci95": [
            0.6428571428571429,
            0.9200263157894736
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.3698630136986301,
          "precision_ci95": [
            0.2602739726027397,
            0.48530462184873946
          ],
          "recall": 0.574468085106383,
          "recall_ci95": [
            0.4313640973630832,
            0.7209302325581395
          ],
          "f1": 0.45,
          "f1_ci95": [
            0.33043478260869563,
            0.5645253632110317
          ],
          "false_fill_rate": 0.6415094339622641,
          "false_fill_rate_ci95": [
            0.5165277777777778,
            0.7708806818181816
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 16,
        "rows_predicted": 357,
        "rows_gold": 221,
        "precision": 0.04481792717086835,
        "recall": 0.07239819004524888,
        "f1": 0.05536332179930796,
        "documents_all_rows_correct": 0.01,
        "precision_ci95": [
          0.016666666666666666,
          0.08454920595773915
        ],
        "recall_ci95": [
          0.027519793892170418,
          0.13001086956521735
        ],
        "f1_ci95": [
          0.020936982882565177,
          0.10169923167678627
        ],
        "documents_all_rows_correct_ci95": [
          0.0,
          0.03
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 0,
        "truncated_replies": 0
      },
      "values_withheld": 44,
      "latency_seconds": {
        "source": "recorded when the call was first made",
        "warm_llm": {
          "n": 98,
          "p50": 2.3719832000066026,
          "p95": 7.313741515011507
        },
        "warm_total": {
          "n": 98,
          "p50": 5.257473450020008,
          "p95": 9.908382310008713
        },
        "cold": {
          "documents": 2,
          "model_load_seconds": [
            69.5487653,
            7.331563
          ],
          "cold_llm_seconds_excluding_load": [
            58.07148729999791,
            4.314486800008768
          ]
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 200,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 1.647
    },
    {
      "system": "S4",
      "source": "evals/results/dev/cord_s4_validation_v1_1_1.json",
      "model": "llama3.2:3b",
      "prompt": "a-1.0",
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.83,
          "precision_ci95": [
            0.75,
            0.9
          ],
          "recall": 0.8469387755102041,
          "recall_ci95": [
            0.7731958762886598,
            0.9183673469387755
          ],
          "f1": 0.8383838383838383,
          "f1_ci95": [
            0.7614213197969543,
            0.9090909090909091
          ],
          "false_fill_rate": 1.0,
          "false_fill_rate_ci95": [
            1.0,
            1.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.6086956521739131,
          "precision_ci95": [
            0.5106274424663482,
            0.7065217391304348
          ],
          "recall": 0.835820895522388,
          "recall_ci95": [
            0.7424120234604106,
            0.9193709677419354
          ],
          "f1": 0.7044025157232704,
          "f1_ci95": [
            0.6124741242038217,
            0.7904261244951957
          ],
          "false_fill_rate": 0.7878787878787878,
          "false_fill_rate_ci95": [
            0.6428571428571429,
            0.9200263157894736
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.4,
          "precision_ci95": [
            0.2911392405063291,
            0.512828947368421
          ],
          "recall": 0.6808510638297872,
          "recall_ci95": [
            0.5434782608695652,
            0.8163265306122449
          ],
          "f1": 0.5039370078740157,
          "f1_ci95": [
            0.38596491228070173,
            0.6179152148664343
          ],
          "false_fill_rate": 0.660377358490566,
          "false_fill_rate_ci95": [
            0.5319148936170213,
            0.7903561827956987
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 16,
        "rows_predicted": 357,
        "rows_gold": 221,
        "precision": 0.04481792717086835,
        "recall": 0.07239819004524888,
        "f1": 0.05536332179930796,
        "documents_all_rows_correct": 0.01,
        "precision_ci95": [
          0.016666666666666666,
          0.08454920595773915
        ],
        "recall_ci95": [
          0.027519793892170418,
          0.13001086956521735
        ],
        "f1_ci95": [
          0.020936982882565177,
          0.10169923167678627
        ],
        "documents_all_rows_correct_ci95": [
          0.0,
          0.03
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 1,
        "truncated_replies": 1
      },
      "values_withheld": 37,
      "latency_seconds": {
        "source": "recorded when the call was first made",
        "warm_llm": {
          "n": 98,
          "p50": 4.731182400007244,
          "p95": 11.198216270007991
        },
        "warm_total": {
          "n": 98,
          "p50": 7.427266749995016,
          "p95": 14.792401384986714
        },
        "cold": {
          "documents": 2,
          "model_load_seconds": [
            69.6028201,
            7.438691
          ],
          "cold_llm_seconds_excluding_load": [
            63.45819709997241,
            8.120966700010575
          ]
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 301,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 0.253
    },
    {
      "system": "S2'",
      "source": "evals/results/dev/cord_s2p_validation_v1_1_1.json",
      "model": "llama3.2:3b",
      "prompt": "a-2.2",
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.7340425531914894,
          "precision_ci95": [
            0.6420852402745996,
            0.8191758307434854
          ],
          "recall": 0.7040816326530612,
          "recall_ci95": [
            0.6099673913043479,
            0.7938144329896907
          ],
          "f1": 0.71875,
          "f1_ci95": [
            0.6282722513089005,
            0.8021317525125626
          ],
          "false_fill_rate": 1.0,
          "false_fill_rate_ci95": [
            1.0,
            1.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.8409090909090909,
          "precision_ci95": [
            0.720855694692904,
            0.9411764705882353
          ],
          "recall": 0.5522388059701493,
          "recall_ci95": [
            0.4266617647058824,
            0.671875
          ],
          "f1": 0.6666666666666666,
          "f1_ci95": [
            0.5471657797129496,
            0.7703734061930783
          ],
          "false_fill_rate": 0.09090909090909091,
          "false_fill_rate_ci95": [
            0.0,
            0.2
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.4931506849315068,
          "precision_ci95": [
            0.37681159420289856,
            0.6081081081081081
          ],
          "recall": 0.7659574468085106,
          "recall_ci95": [
            0.6410256410256411,
            0.8837209302325582
          ],
          "f1": 0.6,
          "f1_ci95": [
            0.4827586206896552,
            0.704
          ],
          "false_fill_rate": 0.5660377358490566,
          "false_fill_rate_ci95": [
            0.42857142857142855,
            0.7021525930851062
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 65,
        "rows_predicted": 422,
        "rows_gold": 221,
        "precision": 0.15402843601895735,
        "recall": 0.29411764705882354,
        "f1": 0.20217729393468117,
        "documents_all_rows_correct": 0.06,
        "precision_ci95": [
          0.10416540556900727,
          0.20833333333333334
        ],
        "recall_ci95": [
          0.20852586887835703,
          0.3813569176192353
        ],
        "f1_ci95": [
          0.13979553791429683,
          0.26687623978751307
        ],
        "documents_all_rows_correct_ci95": [
          0.02,
          0.11
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 0,
        "truncated_replies": 0
      },
      "values_withheld": 0,
      "latency_seconds": {
        "source": "mixed: 99 calls measured in this run, 1 recorded earlier (an aborted run or an earlier system) and replayed",
        "warm_llm": {
          "n": 99,
          "p50": 3.4199010000098573,
          "p95": 6.611833599994931
        },
        "warm_total": {
          "n": 99,
          "p50": 6.3200841999874795,
          "p95": 10.271190230016755
        },
        "cold": {
          "documents": 1,
          "model_load_seconds": [
            4.7619866
          ],
          "cold_llm_seconds_excluding_load": [
            5.6672831999917435
          ]
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 200,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 2.994
    },
    {
      "system": "S3'",
      "source": "evals/results/dev/cord_s3p_validation_v1_1_1.json",
      "model": "llama3.2:3b",
      "prompt": "a-2.2",
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.7931034482758621,
          "precision_ci95": [
            0.7011494252873564,
            0.875
          ],
          "recall": 0.7040816326530612,
          "recall_ci95": [
            0.6099673913043479,
            0.7938144329896907
          ],
          "f1": 0.745945945945946,
          "f1_ci95": [
            0.6559139784946236,
            0.8254140786749481
          ],
          "false_fill_rate": 1.0,
          "false_fill_rate_ci95": [
            1.0,
            1.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.9736842105263158,
          "precision_ci95": [
            0.9142546583850931,
            1.0
          ],
          "recall": 0.5522388059701493,
          "recall_ci95": [
            0.4266617647058824,
            0.671875
          ],
          "f1": 0.7047619047619048,
          "f1_ci95": [
            0.5894736842105263,
            0.8
          ],
          "false_fill_rate": 0.0,
          "false_fill_rate_ci95": [
            0.0,
            0.0
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.5538461538461539,
          "precision_ci95": [
            0.42857142857142855,
            0.676923076923077
          ],
          "recall": 0.7659574468085106,
          "recall_ci95": [
            0.6410256410256411,
            0.8837209302325582
          ],
          "f1": 0.6428571428571429,
          "f1_ci95": [
            0.524249160693222,
            0.7478296217744786
          ],
          "false_fill_rate": 0.4339622641509434,
          "false_fill_rate_ci95": [
            0.30605867346938775,
            0.5714947089947086
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 65,
        "rows_predicted": 410,
        "rows_gold": 221,
        "precision": 0.15853658536585366,
        "recall": 0.29411764705882354,
        "f1": 0.20602218700475436,
        "documents_all_rows_correct": 0.06,
        "precision_ci95": [
          0.10688364581552842,
          0.21463478482952367
        ],
        "recall_ci95": [
          0.20852586887835703,
          0.3813569176192353
        ],
        "f1_ci95": [
          0.14209190397066407,
          0.271387195121951
        ],
        "documents_all_rows_correct_ci95": [
          0.02,
          0.11
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 0,
        "truncated_replies": 0
      },
      "values_withheld": 94,
      "latency_seconds": {
        "source": "recorded when the call was first made",
        "warm_llm": {
          "n": 99,
          "p50": 3.4199010000098573,
          "p95": 6.611833599994931
        },
        "warm_total": {
          "n": 99,
          "p50": 6.250463200014212,
          "p95": 10.171176010018161
        },
        "cold": {
          "documents": 1,
          "model_load_seconds": [
            4.7619866
          ],
          "cold_llm_seconds_excluding_load": [
            5.6672831999917435
          ]
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 200,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 3.31
    },
    {
      "system": "S4'",
      "source": "evals/results/dev/cord_s4p_validation_v1_1_1.json",
      "model": "llama3.2:3b",
      "prompt": "a-2.2",
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.8297872340425532,
          "precision_ci95": [
            0.7473684210526316,
            0.9042553191489362
          ],
          "recall": 0.7959183673469388,
          "recall_ci95": [
            0.7142857142857143,
            0.8775510204081632
          ],
          "f1": 0.8125,
          "f1_ci95": [
            0.7340160966915451,
            0.8877551020408163
          ],
          "false_fill_rate": 1.0,
          "false_fill_rate_ci95": [
            1.0,
            1.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.6404494382022472,
          "precision_ci95": [
            0.5411764705882353,
            0.7391417572463767
          ],
          "recall": 0.8507462686567164,
          "recall_ci95": [
            0.7611940298507462,
            0.9296019170579028
          ],
          "f1": 0.7307692307692307,
          "f1_ci95": [
            0.6394557823129252,
            0.8121212121212121
          ],
          "false_fill_rate": 0.7878787878787878,
          "false_fill_rate_ci95": [
            0.6363636363636364,
            0.925
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.4578313253012048,
          "precision_ci95": [
            0.345679012345679,
            0.5682177790563865
          ],
          "recall": 0.8085106382978723,
          "recall_ci95": [
            0.6874693627450981,
            0.9111403508771928
          ],
          "f1": 0.5846153846153846,
          "f1_ci95": [
            0.47239462714219543,
            0.6906474820143885
          ],
          "false_fill_rate": 0.7169811320754716,
          "false_fill_rate_ci95": [
            0.5961436170212766,
            0.8363729128014842
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 65,
        "rows_predicted": 412,
        "rows_gold": 221,
        "precision": 0.15776699029126215,
        "recall": 0.29411764705882354,
        "f1": 0.20537124802527645,
        "documents_all_rows_correct": 0.06,
        "precision_ci95": [
          0.10619414399650388,
          0.21391814532117365
        ],
        "recall_ci95": [
          0.20852586887835703,
          0.3813569176192353
        ],
        "f1_ci95": [
          0.1415915588835943,
          0.2706086667300198
        ],
        "documents_all_rows_correct_ci95": [
          0.02,
          0.11
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 1,
        "truncated_replies": 1
      },
      "values_withheld": 109,
      "latency_seconds": {
        "source": "mixed: 14 calls measured in this run, 187 recorded earlier (an aborted run or an earlier system) and replayed",
        "warm_llm": {
          "n": 97,
          "p50": 7.676443700007459,
          "p95": 14.051588340008685
        },
        "warm_total": {
          "n": 97,
          "p50": 10.431549100001135,
          "p95": 17.92597274000077
        },
        "cold": {
          "documents": 3,
          "model_load_seconds": [
            4.8176947000000006,
            6.9252932000000005,
            6.735469
          ],
          "cold_llm_seconds_excluding_load": [
            11.8937661999982,
            8.75035230001407,
            9.192992300005438
          ]
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 301,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 3.289
    },
    {
      "system": "S4h",
      "source": "evals/results/dev/cord_s4h_validation_v1_1_1.json",
      "model": "llama3.2:3b",
      "prompt": "a-2.2",
      "n_documents": 100,
      "fields": {
        "total_amount": {
          "n_present": 98,
          "n_absent": 2,
          "precision": 0.8315789473684211,
          "precision_ci95": [
            0.75,
            0.9052631578947369
          ],
          "recall": 0.8061224489795918,
          "recall_ci95": [
            0.7272727272727273,
            0.8877551020408163
          ],
          "f1": 0.8186528497409327,
          "f1_ci95": [
            0.7407118055555555,
            0.8934010152284264
          ],
          "false_fill_rate": 1.0,
          "false_fill_rate_ci95": [
            1.0,
            1.0
          ]
        },
        "subtotal": {
          "n_present": 67,
          "n_absent": 33,
          "precision": 0.6373626373626373,
          "precision_ci95": [
            0.5384615384615384,
            0.7333333333333333
          ],
          "recall": 0.8656716417910447,
          "recall_ci95": [
            0.7777777777777778,
            0.9402985074626866
          ],
          "f1": 0.7341772151898734,
          "f1_ci95": [
            0.6447258036029672,
            0.8143941416529996
          ],
          "false_fill_rate": 0.8181818181818182,
          "false_fill_rate_ci95": [
            0.6841507177033493,
            0.9411764705882353
          ]
        },
        "tax_amount": {
          "n_present": 47,
          "n_absent": 53,
          "precision": 0.4470588235294118,
          "precision_ci95": [
            0.3373493975903614,
            0.5568512156448201
          ],
          "recall": 0.8085106382978723,
          "recall_ci95": [
            0.6874693627450981,
            0.9111403508771928
          ],
          "f1": 0.5757575757575758,
          "f1_ci95": [
            0.4654793103448276,
            0.6811594202898551
          ],
          "false_fill_rate": 0.7547169811320755,
          "false_fill_rate_ci95": [
            0.6378918495297806,
            0.8679245283018868
          ]
        }
      },
      "line_items_row_level": {
        "n_documents": 100,
        "n_documents_with_rows": 100,
        "rows_correct": 84,
        "rows_predicted": 354,
        "rows_gold": 221,
        "precision": 0.23728813559322035,
        "recall": 0.38009049773755654,
        "f1": 0.2921739130434783,
        "documents_all_rows_correct": 0.18,
        "precision_ci95": [
          0.17134388602085232,
          0.3064066852367688
        ],
        "recall_ci95": [
          0.29318094751628143,
          0.4663935574229692
        ],
        "f1_ci95": [
          0.21921594982078854,
          0.36741801353129105
        ],
        "documents_all_rows_correct_ci95": [
          0.11,
          0.26
        ]
      },
      "failures": {
        "crashes": 0,
        "crash_detail": [],
        "failed_extractions": 0,
        "documents_with_a_fallback": 0,
        "pass_fallbacks": 0,
        "retries": 1,
        "truncated_replies": 1
      },
      "values_withheld": 0,
      "latency_seconds": {
        "source": "recorded when the call was first made",
        "warm_llm": {
          "n": 97,
          "p50": 7.676443700007459,
          "p95": 14.051588340008685
        },
        "warm_total": {
          "n": 97,
          "p50": 10.431692300014689,
          "p95": 17.935461839996467
        },
        "cold": {
          "documents": 3,
          "model_load_seconds": [
            4.8176947000000006,
            6.9252932000000005,
            6.735469
          ],
          "cold_llm_seconds_excluding_load": [
            11.8937661999982,
            8.75035230001407,
            9.192992300005438
          ]
        }
      },
      "power": {
        "label": "ac",
        "timings_ac": 301,
        "timings_battery": 0,
        "timings_unknown": 0,
        "source": "Windows Kernel-Power event 105",
        "method": "cache file modification time per recorded timing (audit replay)"
      },
      "lowest_available_system_ram_gib": 3.285
    }
  ]
}
````
