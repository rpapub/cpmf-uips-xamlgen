# ADR-0003: Generator Output Envelope

**Status**: Accepted (revised — `outputs[]` replaces `xaml`, catalog terminology updated)

## Context

The generator output must be more than a bare XAML string. Callers need observability into two distinct concerns:

1. **Opinionated generator behaviour** — every automatic decision the generator made (display name derivation, annotation injection, etc.) must be visible. Callers must not have to guess what the generator did on their behalf.

2. **Input provenance** — the generator consumes activity-catalog files. In the future a resolver may satisfy a requested version with a different resolved version. The output must record what was *actually used*, not only what was requested.

The generator supports two modes (ADR-0001): **fragment** (single unwrapped element) and **full-file** (one complete XAML document per named workflow). The output envelope must accommodate both without separate schemas.

## Decision

The generator returns an **output envelope** — a structured object. The bare XAML string is never the sole return value.

### Envelope structure

```jsonc
{
  "schemaVersion": "1",
  "invocationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "generatedAt": "2026-04-05T12:00:00Z",
  "status": "Success",
  "expressionLanguage": "VisualBasic",
  "outputs": [
    { "name": "Main",               "xaml": "<Activity x:Class=\"Main\" ...>...</Activity>" },
    { "name": "GetTransactionData", "xaml": "<Activity x:Class=\"GetTransactionData\" ...>..." }
  ],
  "effectivePolicy": {
    "displayName": { "pattern": "shortName_hash8" },
    "annotation":  { "alwaysEmit": true }
  },
  "resolvedSources": [
    { "sourceId": "UiPath.System.Activities", "resolvedVersion": "25.10.11" }
  ],
  "inputProvenance": null,
  "diagnostics": []
}
```

Fragment mode produces one entry with `name: null`:

```jsonc
"outputs": [{ "name": null, "xaml": "<log:LogMessage ... />" }]
```

### Field definitions

| Field | Type | Always present | Notes |
|---|---|---|---|
| `schemaVersion` | string | yes | Integer-as-string; increment on breaking changes |
| `invocationId` | string | yes | UUID; unique per generator call |
| `generatedAt` | string | yes | ISO 8601 UTC |
| `status` | string | yes | `enum(Success, PartialSuccess, Failed)` |
| `expressionLanguage` | string | yes | Echoed from input for observability |
| `outputs` | array\|null | yes | `null` when `status` is `Failed`; see below |
| `effectivePolicy` | object | yes | Full merged policy — every opinionated decision visible |
| `resolvedSources` | array | yes | Activity-catalog files consulted: `{ sourceId, resolvedVersion }` per entry |
| `inputProvenance` | object\|null | yes | `null` by default; populated when `verbose=True` |
| `diagnostics` | array | yes | `[]` when none |

### `outputs[]`

Each entry is `{ "name": string|null, "xaml": string }`:

- **Full-file mode**: one entry per `workflows[]` entry; `name` matches `workflows[].name`
- **Fragment mode**: exactly one entry; `name` is `null`
- `outputs` is `null` when `status` is `Failed`

### `effectivePolicy`

Always the complete merged object — built-in defaults overlaid with any caller overrides.

### `resolvedSources`

Records the activity-catalog files the generator actually read. Sourced from `catalog.source.id` and `catalog.source.version` per catalog consumed.

### `inputProvenance` and the `verbose` flag

`null` by default. When `verbose=True`, populated with a per-activity resolution trace:

```jsonc
{
  "activities": [
    {
      "activityId": "UiPath.Core.Activities.LogMessage@UiPath.System.Activities/25.10.11",
      "resolvedFrom": { "sourceId": "UiPath.System.Activities", "resolvedVersion": "25.10.11" }
    }
  ]
}
```

### `diagnostics`

| Stage | Meaning |
|---|---|
| `Resolution` | Locating activity in the activity-catalog data |
| `Generation` | XAML serialisation |
| `PolicyApplication` | Applying or merging policy |

## Consequences

- `outputs[]` is uniform across both modes — consumers iterate the same structure regardless of mode.
- `name: null` in fragment mode is unambiguous and requires no special-casing in schema validation.
- Callers always know exactly what the generator did — `effectivePolicy` eliminates silent magic.
- `resolvedSources` records the exact catalog inputs consumed — output is reproducible and auditable.
