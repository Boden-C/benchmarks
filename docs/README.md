# Documentation

This folder contains the user-facing documentation for the benchmark library.

Primary documents

-   [`architecture.md`](architecture.md) — High-level architecture and component responsibilities.
-   [`design.md`](design.md) — Detailed design and component specifications (mappings to files).
-   [`flow.md`](flow.md) — Runtime execution flow and mode-specific diagrams.
-   [`running.md`](running.md) — Quickstart, configuration, CLI and programmatic usage, and examples.
-   [`todo.md`](todo.md) — Follow-up work and pending considerations.

How the docs are organised

-   High level: the repository root [`README.md`](../README.md) contains a project overview and quickstart.
-   Architecture: [`docs/architecture.md`](architecture.md) contains a concise architecture overview and file mappings.
-   Design & internals: [`docs/design.md`](design.md) contains component-by-component specifications mapped to the codebase.
-   Runtime flow: [`docs/flow.md`](flow.md) contains the primary execution path, simple vs agentic execution details, and textual flow diagrams.
-   Usage & examples: [`docs/running.md`](running.md) covers installation, configuration overrides, CLI flags, and programmatic examples.

Related package READMEs

-   [`../benchmark/README.md`](../benchmark/README.md) — package-level quick reference for the core Python package.
-   [`../benchmark/execution/README.md`](../benchmark/execution/README.md) — detailed README for the execution module (executors, LLM providers, agentic flow).

Quick links

-   Repository README: [`../README.md`](../README.md)
-   Benchmark package README: [`../benchmark/README.md`](../benchmark/README.md)
-   Execution module README: [`../benchmark/execution/README.md`](../benchmark/execution/README.md)
-   Architecture doc: [`architecture.md`](architecture.md)
-   Design doc: [`design.md`](design.md)
-   Execution flow: [`flow.md`](flow.md)
-   Running guide: [`running.md`](running.md)
-   TODO tracker: [`todo.md`](todo.md)

If you want to contribute docs or examples, add them here or under `tests/<benchmark_name>/`.
