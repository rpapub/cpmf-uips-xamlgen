# ADR-0001: Input Surface

**Status**: Accepted (revised — expression language and headless-designer context added)

## Context

This generator is a **headless UiPath Studio designer**: it performs the same pipeline Studio performs interactively — activity resolution, argument binding, namespace mapping, XAML serialisation — but in batch, without a UI. Output must be byte-for-byte compatible with Studio-produced XAML.

The generator needs a defined input format. Candidates considered:

- **Flat argument bag**: `{ "activityId": "...", "arguments": {} }` — simple but single-activity only; breaking change when nesting is needed.
- **Full AST up front**: model every WF construct (Flowchart, StateMachine, TryCatch, ...) — premature; most constructs unimplemented in v0.1.
- **Minimal AST envelope, forward-compatible**: recursive tree with a `kind` discriminator; v0.1 implements a subset; the schema does not need to change as new kinds are added.

UiPath XAML is inherently nested. A bare single activity is valid output, but scope activities (`ApplicationScope`, `BrowserScope`, etc.) carry named child slots (`Body`, `Then`, `Else`, ...) that cannot be expressed in a flat structure. Top-level execution models (`Sequence`, `Flowchart`, `StateMachine`) are structurally distinct from each other and from activity containers.

### Expression language

Activity arguments in WF XAML are not plain values — they are **expressions** evaluated at runtime by either the VB or C# expression evaluator. The target language is a project-level setting in UiPath (`project.json` → `design.expressionLanguage`), not per-activity. It determines which expression wrapper type the serialiser emits (`VisualBasicValue<T>` vs `CSharpValue<T>`).

Argument values in the input AST are treated as **expression strings in the target language**. A string literal in VB is `"Hello"` (double-quoted); an enum reference is `LogLevel.Info`. The generator does not interpret expression content — it passes it through to the appropriate WF expression activity.

Serialisation form (XML attribute vs. child element wrapping) is determined by the `typeConverter` field on the engine-result `Member`:
- `typeConverter` present → attribute form (the type converter handles string-to-value conversion at design time)
- `typeConverter` absent → child element form wrapping the expression in `InArgument<T>` + expression activity

## Decision

### Input document structure

The input is a **document envelope** containing a project-level setting and the AST root:

```json
{
  "expressionLanguage": "VisualBasic",
  "root": { ... }
}
```

`expressionLanguage` is required and applies to all argument values in the entire document.

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
    "Level": "LogLevel.Info",
    "Message": "\"Hello World\""
  },
  "slots": {
    "Body": { "kind": "Sequence", "children": [] }
  }
}
```

- `activityId` follows the PackageFurnace `id` format exactly.
- `arguments` keys are CLR property names as declared in the engine-result `Member.name` field.
- `arguments` values are expression strings in the document's `expressionLanguage`.
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

### Minimal valid input (single activity, VB)

```json
{
  "expressionLanguage": "VisualBasic",
  "root": { "kind": "Activity", "activityId": "...", "arguments": {} }
}
```

## Consequences

- `expressionLanguage` is explicit and required — the generator never guesses or defaults the target language.
- Argument values are opaque expression strings; the generator does not parse or validate expression syntax.
- The serialisation form (attribute vs. child element) is entirely driven by `typeConverter` in the engine-result Member — no heuristics in the generator.
- The input schema is stable: adding `Flowchart` or `StateMachine` support in a later version requires no changes to existing `Activity` or `Sequence` nodes.
- Callers that want only a single activity fragment pass a bare `Activity` node as `root`; no wrapping container is required or implied.
- The generator validates `activityId` and argument names against the supplied engine-result data and rejects unknown identifiers.
