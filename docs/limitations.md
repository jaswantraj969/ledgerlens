# Limitations

Research prototype evaluated on public datasets. Not validated for production use. No compliance certification.

This file grows as limitations are found.

## Deterministic values have no independent evidence

The deterministic extractor copies values from the tokens, so matching them against those tokens proves nothing. Such fields are recorded as `evidence_status: self_sourced` with `evidence_independent: false`, never `exact`, and the feature builder excludes them. Only a value from a different source, such as an LLM pass, gets a real match result. A `self_sourced` field shows where a value was read from, not that it is correct.

## LLM extraction quality on validation

With `llama3.2:3b` and prompts `a-1.0` and `b-1.0`, line items are poor: row-level F1 0.058 for S2, against 0.377 for rules. The model often omits quantity, lists summary lines such as `TOTAL` as items, and confuses columns. It also fills fields that are not printed, with false fill rates of about 0.7 to 0.8 on subtotal and tax. The evidence check cannot catch that, because the number it copies does appear in the document, in a different role. JSON validity is enforced by Ollama's schema constraint, so a high validity rate says nothing about whether values are right.

## Prompt 2.2 helps rows but stays below the rules on CORD

On validation, prompt 2.2 raised row F1 from 0.058 (S2) to 0.202 (S2'), and S4h reached 0.292, against 0.377 for S1. Total F1 fell from 0.814 (S2) to 0.719 (S2'). S4h is below S1 on every CORD field, though the total intervals overlap. Tax false fills stay high (0.57 to 0.76) because a printed number copied into the wrong field passes the evidence check. On synthetic invoices S2' transfers to the held-out layout where rules fail (total F1 1.000 against 0.000), but not for subtotal (0.000) and only partly for invoice number.

## Memory is the binding constraint

With `llama3.2:3b` loaded, free RAM on this machine drops to about 0.3 to 0.4 GiB during runs. Five runs aborted under the 0.4 GiB rule (prompt round, token measurement, two S4' attempts, synthetic S2'), and each was retried from the replay cache. A larger model would make this worse.

## SROIE: removed — official access unavailable; mirror terms unverified

The SROIE labels and vendor groups were deleted, and no SROIE metric exists. CORD has no vendor label, so no real vendor-grouped split was possible on any dataset. The A12 check uses derived CORD layout groups, which approximate layouts, not vendors.

## The risk score is unfitted

`risk_score` uses hand-picked weights and is not a probability. `calibrated_prob` stays null until a calibrator is fitted.

## Amount parsing

One separator followed by exactly three digits is read as thousands grouping (`45.000` is 45000). This suits Indonesian receipts and misreads three-decimal currencies.

## Rule-based extraction does not transfer to unseen wording

On the held-out synthetic layout, S1 scored F1 0.000 on vendor, invoice number, date, subtotal, tax and total, against about 1.000 on development layouts (`evals/results/synthetic_s1_v1_1.md`). Line items and currency held up because they do not depend on label wording. Development-layout scores mostly show fit to known wording.

## Currency scan false fills

The currency scan fills a value on layouts that print no currency: F1 0.000 on the `receipt` layout. The likely cause, unconfirmed, is item words that match ISO codes, such as "Try" or "Sar". It is left unfixed, because rules may not change after reading held-out results without a new protocol.

## Synthetic evaluation scope

The synthetic evaluation covers five single-page layouts. Rotated, low-DPI and multi-page variants exist in the generator but are outside this run.

## Native-text PDFs only

The working parser reads embedded text. Scanned PDFs and images yield no tokens until OCR is added.
