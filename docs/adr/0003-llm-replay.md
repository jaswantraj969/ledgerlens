# ADR-0003: LLM provider abstraction and replay cache

Status: Accepted  
Date: 2026-11-05

## Decision
An `LLMProvider` protocol with LiteLLM for hosted and Ollama backends, plus a `replay` provider. Every call is cached on disk under `sha256(model, prompt, params, schema_version)`. Evaluations default to replay. A replay miss is an error, never a silent live call.

## Why
Results must reproduce with no network or key (R7). Only the synthetic smoke cache is committed; caches from licensed datasets stay local.

## Amendment, 2026-11-07
The Ollama path calls Ollama's HTTP API directly with `httpx`, not through LiteLLM. That is a deviation for this one provider: `httpx` is already a dependency, and structured output and load timing are exposed directly. Hosted providers still use LiteLLM, which is not implemented yet. A provider failure or replay miss during extraction falls back to the deterministic extractor with the source marked. An evaluation run must treat any fallback as a counted failure.

## Consequences
The default pipeline needs no LLM at all: the deterministic extractor is the offline default. LLM-based systems S2-S5 need a working local model to fill the cache once.
