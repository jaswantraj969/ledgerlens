# Limitations

Research prototype evaluated on public datasets. Not validated for production use. No compliance certification.

This file grows as limitations are found.

## Deterministic values have no independent evidence

The deterministic extractor copies values from the tokens, so matching them against those tokens proves nothing. Such fields are recorded as `evidence_status: self_sourced` with `evidence_independent: false`, never `exact`, and the feature builder excludes them. Only a value from a different source, such as an LLM pass, gets a real match result. A `self_sourced` field shows where a value was read from, not that it is correct.

## The risk score is unfitted

`risk_score` uses hand-picked weights and is not a probability. `calibrated_prob` stays null until a calibrator is fitted.

## Amount parsing

One separator followed by exactly three digits is read as thousands grouping (`45.000` is 45000). This suits Indonesian receipts and misreads three-decimal currencies.

## Synthetic invoices share one layout

The generator renders a single template today. It has no rotated scans, low-DPI renders or noise yet, and passing tests on it says little about real documents.

## Native-text PDFs only

The working parser reads embedded text. Scanned PDFs and images yield no tokens until OCR is added.
