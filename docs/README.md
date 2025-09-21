# Documentation

This folder contains the user-facing documentation for the benchmark library.

Primary documents

- `architecture.md` — Detailed architecture and component specifications.
- `architecture.md` — Detailed architecture and component specifications.
- `flow.md` — Runtime execution flow and mode-specific diagrams (extracted from architecture).
- `running.md` — Quickstart, configuration, CLI and programmatic usage, and examples.

How the docs are organised

- High level: the repository root `README.md` contains a project overview and quickstart.
- Design & internals: `docs/architecture.md` contains a component-by-component description that maps to the code under `benchmark/`.
- Design & internals: `docs/architecture.md` contains a component-by-component description that maps to the code under `benchmark/`.
- Runtime flow: `docs/flow.md` contains the primary execution path and executor-mode details.
- Usage & examples: `docs/running.md` covers installation, configuration overrides, CLI flags, and programmatic examples.

Related package READMEs

- `benchmark/README.md` — package-level quick reference for the core Python package.
- `benchmark/execution/README.md` — detailed README for the execution module (executors, LLM providers, agentic flow).

Quick links

- Repository README: `../README.md`
- Benchmark package README: `../benchmark/README.md`
- Execution module README: `../benchmark/execution/README.md`
- Architecture doc: `architecture.md`
- Running guide: `running.md`
- Execution flow: `flow.md`
- Running guide: `running.md`

If you want to contribute docs or examples, add them here or under `tests/<benchmark_name>/`.
