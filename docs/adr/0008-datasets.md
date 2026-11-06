# ADR-0008: Datasets and licences

Status: Accepted  
Date: 2026-11-05

## Decision
CORD v2 (CC BY 4.0) and the seeded synthetic set are in scope first. SROIE is research-only unless a clearly licensed source is verified. DocILE needs a human access request. FUNSD is excluded from the main schema. No dataset file is committed; download scripts carry checksums.

## Consequences
Each adapter declares its evaluable fields after inspecting the actual labels; a field a dataset does not label is never evaluated. Synthetic results are always reported separately. Inspection confirmed CORD has no vendor id and labels neither vendor_name, invoice_number, invoice_date nor currency (see evals/datasets/LICENSES.md), so its grouped split uses derived layout groups.
