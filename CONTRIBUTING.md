# Contributing

Keep each research assumption visible in a versioned configuration and in `STRATEGY_SPEC.md`. New strategy versions must not overwrite old run configurations. Changes to simulation semantics need deterministic fixtures and tests. Preserve UTC internally and use IANA time zones for wall-clock rules. Never add live broker execution to this research MVP. Run `python -m pytest` and `ruff check backend tests` before submitting changes.
