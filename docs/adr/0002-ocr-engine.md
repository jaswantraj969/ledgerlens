# ADR-0002: Parsing and OCR engine

Status: Proposed (pending the Docling install test)  
Date: 2026-11-05

## Proposal
Docling for PDFs behind a `Parser` interface, RapidOCR (ONNX) for scans and images. Tesseract is absent here. PaddleOCR is not tried unless RapidOCR fails.

## To settle before acceptance
Docling pulls in torch and model downloads on a slow link. Record the install result, then the per-page CPU time. Words, bboxes and confidences must come from the engine; missing confidence stays null.

## Fallback if Docling is impractical here
A `pypdfium2` native-text parser plus direct RapidOCR. That is a deviation from the specification and this ADR must say so with the evidence.
