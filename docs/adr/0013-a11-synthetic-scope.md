# ADR-0013: A11 on synthetic data is narrowed to S1 and S2′

Status: Accepted
Date: 2026-11-12

## Context
Acceptance criterion A11 asks for S1 to S5 on at least CORD and the synthetic set. CORD now has S1, S2′, S3′, S4′, S4h, S5-S1 and S5-S4h on test (`evals/results/final/`). The synthetic set has S1 (metrics 1.1.1, `evals/results/synthetic_s1_v1_1_1.json`) and S2′ (`evals/results/synthetic_s2p_v1_1_1.json`), each on 40 native-PDF and 20 OCR documents for each of five layouts, one of them held out.

## Decision
**On the synthetic set, A11 is narrowed to S1 and S2′. S3, S4, S4h and S5 are not run on synthetic data.**

## Reasons
- **S5 needs synthetic calibration data that does not exist.** S5 fits its calibrator on training predictions and sets thresholds on a separate validation set. The synthetic set is an evaluation set only: there is no synthetic train or validation split, and no S4h predictions or per-field records on synthetic documents. A fair S5 on synthetic data needs both splits generated under a new pre-registered protocol, S4h run on all of them, and then a calibrator and thresholds. Calibrating on CORD and scoring on synthetic documents would test a domain shift, not S5 as defined.
- **The LLM runs are slow on this hardware.** The S2′ synthetic run needed 300 LLM calls (one pass per document) and took about 30 minutes in total, including one memory abort (`docs/progress/logs/run-synthetic-s2p.log`). S4 and S4h add a second pass on every document, and S5 would add S4h on new train and validation splits. Memory aborts are frequent here (8 in the final test read, 9 in the 800-document train run), with about 2 to 6 GiB of free RAM depending on what else is open.
- **The question the synthetic set answers is already answered.** It tests transfer to a layout the rules never saw. The S1 and S2′ comparison answers that: S1 scores 0.000 on six header fields of the held-out layout, and S2′ recovers four of them.

## Consequences
- A11 stays IN PROGRESS for the synthetic part, with its scope stated here. The synthetic claims in the README cover S1 and S2′ only.
- S3′, S4′ and S4h have no synthetic numbers. Whether the evidence check or the hybrid rules help on unseen layouts is not measured.
- Revisiting this needs a new protocol (synthetic train and validation splits, S4h on them, S5 fitted on them), and preferably a machine with more RAM.
