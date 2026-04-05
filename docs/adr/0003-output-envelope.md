# ADR-0003: Generator Output Envelope

**Status**: Accepted

## Context

The generator output must be more than a bare XAML string. Callers need observability into two distinct concerns:

1. **Opinionated generator behaviour** — every automatic decision the generator made (display name derivation, annotation injection, etc.) must be visible. Callers must not have to guess what the generator did on their behalf.

2. **Input provenance** — the generator consumes PackageFurnace engine-result files. In the future a resolver may satisfy a requested version with a different resolved version. The output must record what was *actually used*, not only what was requested.

## Decision

The generator returns an **output envelope** — a structured object containing the XAML and all metadata. The bare XAML string is never the sole return value.

### Envelope structure

```jsonc
{
  "schemaVersion": "1",
  "invocationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "generatedAt": "2026-04-05T12:00:00Z",
  "status": "Success",
  "xaml": "<log:LogMessage ... />",
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

### Field definitions

| Field | Type | Always present | Notes |
|---|---|---|---|
| `schemaVersion` | string | yes | Integer-as-string; increment on breaking changes |
| `invocationId` | string | yes | UUID; unique per generator call |
| `generatedAt` | string | yes | ISO 8601 UTC |
| `status` | string | yes | `enum(Success, PartialSuccess, Failed)` — same contract as PackageFurnace |
| `xaml` | string\|null | yes | `null` when `status` is `Failed` |
| `effectivePolicy` | object | yes | Full merged policy object actually applied — every opinionated decision is visible |
| `resolvedSources` | array | yes | Engine-result files actually consulted: `{ sourceId, resolvedVersion }` per entry |
| `inputProvenance` | object\|null | yes | `null` when not verbose; full resolution trace when verbose (see below) |
| `diagnostics` | array | yes | `[]` when none; same `{ level, stage, message, context }` shape as PackageFurnace |

### `effectivePolicy`

Always the complete merged object — built-in defaults overlaid with any caller overrides. The caller sees exactly what was applied, regardless of how much they overrode. This is the primary observability mechanism for generator behaviour.

### `resolvedSources`

Records the engine-result files the generator actually read to produce the output. In v0.1 this mirrors the engine-result files passed in by the caller. When a future resolver substitutes a different version than requested, this field reflects the substituted version — not the requested one.

### `inputProvenance` and the `verbose` flag

`inputProvenance` is `null` by default. When the caller passes `verbose=True`, it is populated with a per-activity resolution trace:

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

This is forward-compatible: when a resolver introduces version substitution, the trace will show the originally requested `activityId` alongside the resolved source. In v0.1 the two are always identical.

### `diagnostics`

Same shape as PackageFurnace diagnostics. `stage` values relevant to the generator:

| Stage | Meaning |
|---|---|
| `Resolution` | Locating activity in the provided engine-result data |
| `Generation` | XAML serialisation |
| `PolicyApplication` | Applying or merging policy |

## Consequences

- Callers always know exactly what the generator did — `effectivePolicy` eliminates silent magic.
- Output is reproducible and auditable: `resolvedSources` records the exact inputs consumed.
- `verbose=True` is available for debugging resolution without polluting normal output.
- The envelope shape is consistent with PackageFurnace conventions; consumers that handle both have a uniform contract.
