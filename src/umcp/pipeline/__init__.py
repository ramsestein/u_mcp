"""
pipeline — Anonymization engine (shared core).

- detectors/: Entity detection modules
  - base.py: Abstract Entity + EntityDetector
  - unicode.py: Unicode sanitization (zero-width, BIDI, PUA)
  - regex_detector.py: Structured patterns (IPs, emails, NHC, DNI...)
  - aho_corasick.py: Dictionary-based detection (clinical entities, stopwords)
  - bert_detector.py: BERT NER (carmen-anon + meddocan)
  - ensemble.py: Fusion + deduplication + label priority
- vault/: Surrogate store
  - vault.py: SQLite session-scoped bidirectional mapping
  - surrogates.py: SHA-256 reproducible surrogate generation
- date_preserver.py: Date detection and preservation
- whitelist.py: Safe clinical terms (medications, diagnoses)
"""