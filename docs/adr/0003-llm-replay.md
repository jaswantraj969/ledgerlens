# ADR-0003: LLM provider abstraction and replay cache

Status: Accepted  
Date: 2026-11-05

## Decision
An `LLMProvider` protocol with LiteLLM for hosted and Ollama backends, plus a `replay` provider. Every call is cached on disk under `sha256(model, prompt, params, schema_version)`. Evaluations default to replay. A replay miss is an error, never a silent live call.

## Why
Results must reproduce with no network or key (R7). Only the synthetic smoke cache is committed; caches from licensed datasets stay local.

## Consequences
The default pipeline needs no LLM at all: the deterministic extractor is the offline default. LLM-based systems S2-S5 need a working local model to fill the cache once.
