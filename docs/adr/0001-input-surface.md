# ADR-0001: Input Surface

**Status**: Accepted

## Context

The generator needs a defined input format. Candidates considered:

- **Flat argument bag**: `{ "activityId": "...", "arguments": {} }` — simple but single-activity only; breaking change when nesting is needed.
- **Full AST up front**: model every WF construct (Flowchart, StateMachine, TryCatch, ...) — premature; most constructs unimplemented in v0.1.
- **Minimal AST envelope, forward-compatible**: recursive tree with a `kind` discriminator; v0.1 implements a subset; the schema does not need to change as new kinds are added.

UiPath XAML is inherently nested. A bare single activity is valid output, but scope activities (`ApplicationScope`, `BrowserScope`, etc.) carry named child slots (`Body`, `Then`, `Else`, ...) that cannot be expressed in a flat structure. Top-level execution models (`Sequence`, `Flowchart`, `StateMachine`) are structurally distinct from each other and from activity containers.

## Decision

The generator input is a **recursive AST** with a `kind` discriminator on every node.

### Node kinds

| Kind | Description | v0.1 |
|---|---|---|
| `Activity` | Leaf or scope-container; has `activityId`, `arguments`, optional `slots` | implemented |
| `Sequence` | Ordered container; has `children[]` | implemented |
| `Flowchart` | Graph-based container | reserved, not implemented |
| `StateMachine` | State/transition container | reserved, not implemented |

The root node may be any kind, including a bare `Activity`. The generator does not impose a container.

### Activity node

```json
{
  "kind": "Activity",
  "activityId": "{fullName}@{sourceId}/{sourceVersion}",
  "arguments": {
    "ArgumentName": "<expression or literal>"
  },
  "slots": {
    "Body": { "kind": "Sequence", "children": [] }
  }
}
```

- `activityId` follows the PackageFurnace `id` format exactly.
- `arguments` keys are CLR property names as declared in the engine-result `Member.name` field.
- `slots` keys are CLR property names of members with `memberKind: Child`.
- `slots` is omitted when the activity has no child members or the caller does not supply nested content.

### Sequence node

```json
{
  "kind": "Sequence",
  "children": [
    { "kind": "Activity", "activityId": "...", "arguments": {} }
  ]
}
```

- `children` is an ordered array of any node kind.

### Minimal valid input (single activity)

```json
{ "kind": "Activity", "activityId": "...", "arguments": {} }
```

## Consequences

- The input schema is stable: adding `Flowchart` or `StateMachine` support in a later version requires no changes to existing `Activity` or `Sequence` nodes.
- Callers that want only a single activity fragment pass a bare `Activity` node; no wrapping container is required or implied.
- The generator validates `activityId` and argument names against the supplied engine-result data and rejects unknown identifiers.
