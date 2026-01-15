
# Sync Protocol Framework

## Goals
- Offline-first
- Hash-based deduplication
- Folder-scoped sync per device
- Stateless ingest service

## Model
1. Client hashes file
2. Server checks existence
3. Upload only if missing
4. Metadata enrichment async

No delete propagation in v1.
