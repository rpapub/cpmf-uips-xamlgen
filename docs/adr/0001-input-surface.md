# ADR-0001: Input Surface

**Status**: Accepted (revised — multi-workflow and full XAML file generation added)

## Context

This generator is a **headless UiPath Studio designer**: it performs the same pipeline Studio performs interactively — activity resolution, argument binding, namespace mapping, XAML serialisation — but in batch, without a UI. Output must be byte-for-byte compatible with Studio-produced XAML.

The generator scope includes **full `.xaml` file generation**: a single input document may describe multiple named workflows, each producing one complete XAML file. It also supports **fragment mode** — emitting a single unwrapped activity or sequence element without a file wrapper.

### Expression language

Activity arguments in WF XAML are not plain values — they are **expressions** evaluated at runtime by either the VB or C# expression evaluator. The target language is a project-level setting in UiPath (`project.json` → `design.expressionLanguage`), not per-activity. It determines which expression wrapper type the serialiser emits (`VisualBasicValue<T>` vs `CSharpValue<T>`).

Argument values in the input AST are treated as **expression strings in the target language**. The generator does not interpret expression content — it passes it through to the appropriate WF expression activity.

Serialisation form (XML attribute vs. child element wrapping) is determined by the `typeConverter` field on the activity-catalog `member`:
- `typeConverter` present → attribute form
- `typeConverter` absent → child element form wrapping the expression in `InArgument<T>` + expression activity

## Decision

### Generation modes

Two mutually exclusive modes, selected by which top-level key is present in the input document:

| Mode | Key | Output |
|---|---|---|
| **Full-file** | `workflows[]` | One complete `<Activity x:Class="...">` XAML document per workflow entry |
| **Fragment** | `root` | Single unwrapped XML element or tree; no `x:Class`, no file wrapper |

### Input document structure

```json
{
  "expressionLanguage": "VisualBasic",
  "workflows": [
    { "name": "Main",               "root": { "kind": "Sequence", "children": [...] } },
    { "name": "GetTransactionData", "root": { "kind": "Activity", "activityId": "..." } }
  ]
}
```

Or fragment mode:

```json
{
  "expressionLanguage": "VisualBasic",
  "root": { "kind": "Activity", "activityId": "...", "arguments": {} }
}
```

- `expressionLanguage` is required in both modes and applies to all argument values.
- `workflows[].name` maps directly to the XAML `x:Class` attribute.
- `workflows[]` and `root` must not both be present.

### Node kinds

| Kind | Description | v0.1 |
|---|---|---|
| `Activity` | Leaf or scope-container; has `activityId`, `arguments`, optional `slots` | implemented |
| `Sequence` | Ordered container; has `children[]` | implemented |
| `Flowchart` | Graph-based container | reserved, not implemented |
| `StateMachine` | State/transition container | reserved, not implemented |

### Activity node

```json
{
  "kind": "Activity",
  "activityId": "{fullName}@{source.id}/{source.version}",
  "arguments": {
    "Level": "LogLevel.Info",
    "Message": "\"Hello World\""
  },
  "slots": {
    "Body": { "kind": "Sequence", "children": [] }
  }
}
```

- `activityId` follows the activity-catalog `activity.id` format exactly.
- `arguments` keys are CLR property names (`member.name` in the activity-catalog).
- `arguments` values are expression strings in the document's `expressionLanguage`.
- `slots` keys are CLR property names of members with `memberKind: child`.

### Sequence node

```json
{
  "kind": "Sequence",
  "children": [
    { "kind": "Activity", "activityId": "...", "arguments": {} }
  ]
}
```

## Consequences

- `expressionLanguage` is explicit and required — the generator never guesses the target language.
- `workflows[].name` supplies `x:Class` — no separate mechanism needed.
- Fragment mode and full-file mode are unambiguous from the document structure.
- The node kind set is stable: adding `Flowchart` or `StateMachine` requires no changes to `Activity` or `Sequence` nodes.
- The generator validates `activityId` and argument names against the supplied activity-catalog data and rejects unknown identifiers.
