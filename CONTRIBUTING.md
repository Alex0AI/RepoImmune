# Contributing

1. Open an issue describing the evidence source and failure mode.
2. Create a focused branch; do not commit third-party repositories, credentials, model weights or generated files over 50MB.
3. Add a Behavior Card only when code/test/commit evidence supports it. Use `heuristic` or abstain when uncertain.
4. Run `pytest`, `coverage run -m pytest`, `ruff check .`, and `mypy src/repoimmune`.
5. Include negative controls for new matching logic and update the data card for a new source.

By participating, you agree to the Code of Conduct and license contributions under Apache-2.0.

