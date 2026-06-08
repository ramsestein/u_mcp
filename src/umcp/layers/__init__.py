"""
layers — Double-plane anonymization/deanonymization layers.

- msg_interceptor.py: Transparent layer between User↔LLM
- resource_pipeline.py: Intercepts resource access, anonymizes before LLM context
- tool_dispatcher.py: Routes tool calls (secure → deanonymize/resp re-anonymize,
  insecure → fully anonymized)
"""