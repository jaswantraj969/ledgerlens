# ADR-0007: Confidence protocol

Status: Accepted  
Date: 2026-11-05

## Decision
Follow section 4 of the specification. `risk_score` is a heuristic and labelled as one. `calibrated_prob` stays null unless a calibrator fitted for that schema and model exists. Calibrators fit on train, thresholds are chosen on calibration, and test is read once per reported configuration. Bootstrap CIs resample documents, not fields.

## Why
Fields from one document are correlated, so resampling fields would understate uncertainty. Thresholds moved after seeing test results would invalidate the reported precision.

## Consequences
Normalisation rules are versioned and frozen before experiments. If a target precision is missed on test, the miss is reported as it stands.
