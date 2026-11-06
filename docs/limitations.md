# Limitations

Research prototype evaluated on public datasets. Not validated for production use. No compliance certification.

This file grows as limitations are found.

## Evidence matching is not independent for the deterministic extractor

The deterministic extractor reads values from the same tokens the evidence matcher searches, so `evidence_status` is almost always `exact` for it. That result says the value came from the document, not that it is the right value. The signal only carries real information for LLM-extracted values.

## The risk score is unfitted

`risk_score` uses hand-picked weights and is not a probability. `calibrated_prob` stays null until a calibrator is fitted.

## Amount parsing

One separator followed by exactly three digits is read as thousands grouping (`45.000` is 45000). This suits Indonesian receipts and misreads three-decimal currencies.

## Synthetic invoices share one layout

The generator renders a single template today. It has no rotated scans, low-DPI renders or noise yet, and passing tests on it says little about real documents.

## Native-text PDFs only

The working parser reads embedded text. Scanned PDFs and images yield no tokens until OCR is added.
