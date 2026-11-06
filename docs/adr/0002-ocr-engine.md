# ADR-0002: Parsing and OCR engine

Status: Accepted — deviation: Docling deferred to optional parser; reason: install unreliable on this network  
Date: 2026-11-06

## Decision
`pypdfium2` reads native PDF text and renders pages. RapidOCR (ONNX, bundled PP-OCRv6 models) reads images and scanned pages. Both sit behind the `Parser` interface, and `AutoParser` chooses per page. The specification names Docling as the default, so this is a recorded deviation, approved in the supervisor review of 2026-11-06.

## Why
Two Docling installs failed or hung here, one on an archive error and one on a dead connection. It pulls in torch and further model downloads. RapidOCR installed and runs on CPU, returning word boxes and word scores.

## Consequences
- Tokens carry engine text, box and score. A missing score stays null, and a line the engine does not split stays one token, because slicing it would invent coordinates.
- Docling stays available as the optional `docling` extra but has no `Parser` implementation yet.
- Layout analysis such as table structure is not available. Extraction relies on token geometry.
- Future ablation: Docling vs fallback.
