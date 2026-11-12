# Case study (draft): measuring a document-extraction system honestly

Research prototype evaluated on public datasets. Not validated for production use.

## The problem
Receipt and invoice extraction tools often report accuracy that no one can reproduce. I wanted a system whose every reported number traces to a file and a command, and whose weaknesses are stated as plainly as its strengths.

## What I built
- **Application:** a Docker Compose stack with a FastAPI service, an RQ worker, PostgreSQL, Redis and a React review app served by Caddy.
- **Pipeline:** the worker parses each document, using native PDF text or CPU OCR, and extracts fields with tuned rules or a local LLM (llama3.2:3b through Ollama). It verifies each value against the page, scores its risk, and routes it to review or acceptance.
- **Review:** reviewers see each value's evidence box on the page image.

## How it was evaluated
- **Pre-registration:** every test protocol was committed before the test split was read. The CORD v2 test split (100 receipts) was then read once, by one unattended script, from a clean commit.
- **Controls in that run:** a pre-flight check, resumable steps with hash-checked completion markers, and AC power only.
- **Integrity:** independent checks confirmed every output hash and the thresholds.
- **Systems compared:** tuned rules (S1); the LLM alone (S2′, S3′); a merge of the two (S4′); a pre-registered hybrid (S4h); and a calibrated router (S5) that decides which values skip human review.

## Results (CORD v2 test, 100 receipts)
| System | Total F1 [95% CI] | Tax F1 [95% CI] | Row-level F1 [95% CI] |
|---|---|---|---|
| S1, tuned rules | 0.793 [0.712, 0.866] | 0.763 [0.622, 0.881] | 0.365 [0.263, 0.471] |
| S4h, rules plus LLM | 0.827 [0.753, 0.898] | 0.508 [0.393, 0.609] | 0.253 [0.168, 0.343] |

Source: `evals/results/final/cord_test_comparison_v1_1_1.md`.

- **The LLM did not beat the tuned rules on CORD.** It was slightly ahead on total, with overlapping intervals, and behind on tax and line items.
- **On an unseen synthetic invoice layout it did transfer where the rules failed** (`evals/results/synthetic_s1_v1_1_1.md`, `evals/results/synthetic_s2p_v1_1_1.md`).
- **Review routing (S5-S1, target precision 0.98):** 19% of header fields skipped review (0.193), with measured precision 0.966 [0.906, 1.000]. That is below the target point, but the interval contains it. Only 3 of 253 line-item rows were accepted, so a person reviews essentially every line item. Source: `evals/results/final/cord_s5_test_v1_1_1.md`.
- **Blur:** strong blur cut the mean of four F1 scores for the rules from 0.681 to 0.446. Source: `evals/results/final/cord_degradation_test_v1_1_1.md`.

## What went wrong, and what I did about it
- **Near-duplicates in the dataset:** after the test read, I found that 7 test receipts have near-copies in CORD's train or validation splits. I registered a sensitivity check before computing it. On the remaining 93, no comparison between the rules and the hybrid changed direction (`evals/results/final/cord_test_dedup_sensitivity_v1_1_1.md`).
- **Memory:** on a laptop, long LLM runs hit a free-memory abort rule. The final run had 8 memory aborts (`evals/results/final/final-run-metadata-20261112T073516Z.json`); each one resumed from cached replies with identical settings.
- **Not verified:** the LLM mode inside Docker has not been verified end to end.

## What I would do next
- A larger, independent test set with vendor-level splits.
- Calibration fitted on more data, so the routing thresholds hold their precision.
- Line-item extraction good enough to route rows automatically.
