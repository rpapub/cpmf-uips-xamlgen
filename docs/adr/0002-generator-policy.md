# ADR-0002: Opinionated GeneratorPolicy and Caller Overrides

**Status**: Accepted (revised — Config/Policy split; updated code example)

## Context

XAML attributes such as `DisplayName`, annotations, and designer layout hints are not part of a workflow's logic. The caller should not be required to supply them. At the same time, omitting them produces XAML that is technically valid but behaves unexpectedly in UiPath Studio (e.g., duplicate display names, missing layout hints causing the designer to reformat on first open).

The generator must be **opinionated by default** — it fills in these values automatically — while remaining **overridable** by callers that have specific requirements.

### Config vs Policy

Two distinct caller-configurable layers exist:

- **Config** — operational/infrastructure concerns: where to find catalogs, resolution strategy, semver fallback. Defined in a separate Config file and covered by its own defaults. See `schemas/v0.1/xamlgen-config.schema.json`.
- **Policy** — generation opinions: display name format, annotation behaviour, rendering choices. This ADR covers Policy only.

## Decision

Generator behaviour that is not driven by the caller's generate input is encapsulated in a `GeneratorPolicy` object, loaded from a **policy file** (TOML). Policies are applied after catalog resolution and before XAML serialisation.

### Policy file resolution order

1. **Built-in default policy file** — shipped with the package at `cpmf_uips_xamlgen/policy/default.toml`; always present, always valid.
2. **Caller-supplied policy file** — an optional path passed at call time; merged over the defaults. Unknown keys are rejected.

The generator never falls back to hardcoded values in source code. All defaults live in `default.toml` and are therefore inspectable, diffable, and forkable without touching code.

Callers may override individual policy fields; they may not disable the policy mechanism entirely.

### Defined policies (v0.1)

| Policy | Default | Notes |
|---|---|---|
| `displayName` | `{activityShortName}_{hash8}` | Short name is the last segment of `fullName`; hash is 8 hex characters derived from `activityId`. Guarantees uniqueness within a generated document. |
| `annotation` | `""` (empty string) | Annotation element is always emitted. Caller may supply content; the element is never omitted. |

### TBD policies (candidates, not yet decided)

| Policy | Candidate default |
|---|---|
| `hintSize` | emit `sap:VirtualizedContainerService.HintSize` as written by Studio; prevents designer reformat on first open |
| `requiredArgumentMissing` | `error` — fail fast rather than emit invalid XAML |
| `xName` | omit by default; optionally generate a stable `x:Name` alongside `DisplayName` |

### Override interface (v0.1)

The caller optionally passes a path to their own policy file. Unknown keys are rejected.

```python
generate(ast_doc, catalogs, policy_file="/path/to/my-policy.toml")
```

The caller's file is merged over the built-in defaults: only keys present in the caller's file are overridden. All other policies remain at their built-in defaults.

### Policy is not part of the AST

Policy fields must not appear inside the AST input. The AST describes *what* to generate; policy describes *how* the generator behaves. Mixing them would couple caller intent to generator implementation details.

## Consequences

- The generator always produces well-formed, Studio-compatible XAML without requiring the caller to know Studio conventions.
- Callers with specific needs (e.g., deterministic `DisplayName` for test fixtures) supply their own policy file without forking the generator.
- The built-in `default.toml` is the authoritative, human-readable record of all generator defaults; additions require updating that file and this ADR.
