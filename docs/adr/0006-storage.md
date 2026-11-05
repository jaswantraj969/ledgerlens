# ADR-0006: Document storage

Status: Accepted  
Date: 2026-11-05

## Decision
A `StorageBackend` interface with a local-filesystem implementation. Keys are generated (`org/<id>/<sha256>`); uploaded filenames never reach a path. S3/MinIO is documented as optional and is not implemented.
