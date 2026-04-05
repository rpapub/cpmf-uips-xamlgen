# ADR-0001: Input Surface

**Status**: Revised — two-step model replaces tool-owned AST

## Context

Earlier versions of this ADR defined the generator's input as a tool-owned "AST light" format
(`ActivityNode`, `SequenceNode`, generation modes). That was wrong: the **AST is the caller's
responsibility**. The tool's job is to help callers build a valid AST (scaffold step) and then
consume it (generate step).

The generator operates as a **headless UiPath Studio designer** — it performs activity resolution,
argument binding, namespace mapping, and XAML serialisation without a UI. Output must be
compatible with Studio-produced XAML.

## Decision

### Two-step model

The tool exposes two distinct operations:

| Step | Input | Output |
|---|---|---|
| **Scaffold** | `activityId` + catalog | Argument template — describes what the activity requires; `value: null` slots for the caller to fill |
| **Generate** | Filled argument template(s) + catalog | XAML output envelope |

The scaffold step is **support infrastructure**: it reads the catalog and returns a structured
description of an activity's arguments (names, directions, types, required/optional, enum values).
The caller uses this to construct their generate input. They are not required to use scaffold — it
exists to prevent callers from having to read the catalog schema directly.

### Schemas

Each step has a dedicated input and output schema (all under `schemas/v0.1/`):

| Schema | Purpose |
|---|---|
| `xamlgen-scaffold-input.schema.json` | Scaffold input: `activityId` only |
| `xamlgen-scaffold-output.schema.json` | Scaffold output: `ArgumentDescriptor[]` with `value: null` |
| `xamlgen-generate-input.schema.json` | Generate input: filled nodes + `expressionLanguage` |
| `xamlgen-generate-output.schema.json` | Generate output: XAML envelope (see ADR-0003) |

### Scaffold output

The scaffold output describes one activity:

```jsonc
{
  "activityId": "UiPath.Core.Activities.LogMessage@UiPath.System.Activities/25.10.11",
  "fullName": "UiPath.Core.Activities.LogMessage",
  "displayName": "Log Message",
  "description": "Logs a message at the specified level.",
  "arguments": [
    {
      "name": "Level",
      "displayName": "Log Level",
      "direction": "In",
      "dataType": "UiPath.Core.Activities.LogLevel",
      "required": true,
      "typeConverter": null,
      "enumValues": ["LogLevel.Trace", "LogLevel.Info", "LogLevel.Warn", "LogLevel.Error"],
      "value": null        // ← caller fills this in
    },
    {
      "name": "Message",
      "displayName": "Message",
      "direction": "In",
      "dataType": "System.String",
      "required": true,
      "typeConverter": "InArgument`1",
      "enumValues": null,
      "value": null        // ← caller fills this in
    }
  ]
}
```

### Generate input

The caller constructs this document — typically by filling in scaffold output values:

```jsonc
{
  "expressionLanguage": "VisualBasic",
  "root": {
    "kind": "Activity",
    "activityId": "UiPath.Core.Activities.LogMessage@UiPath.System.Activities/25.10.11",
    "arguments": {
      "Level": "LogLevel.Info",
      "Message": "\"Hello World\""
    }
  }
}
```

Or full-file mode (multiple named workflows → one XAML file each):

```jsonc
{
  "expressionLanguage": "VisualBasic",
  "workflows": [
    { "name": "Main", "root": { "kind": "Sequence", "children": [...] } }
  ]
}
```

### Expression language

Activity arguments in WF XAML are **expressions** evaluated at runtime by either the VB or C#
evaluator. The target language is a project-level setting (`project.json` →
`design.expressionLanguage`), not per-activity. The caller declares it once at the top of the
generate input document.

Argument values in the generate input are expression strings in the declared language. The
generator passes them through to the appropriate WF expression activity without interpreting them.

Serialisation form (XML attribute vs. child element) is determined by `typeConverter` on the
catalog member — exposed in the scaffold output so the caller has full visibility, but handled
automatically by the generator.

### Node kinds

The generate input supports the following node kinds (discriminated by `kind`):

| Kind | v0.1 |
|---|---|
| `Activity` | implemented |
| `Sequence` | implemented |
| `Flowchart` | reserved |
| `StateMachine` | reserved |

Container activities that accept nested nodes (e.g. `Body`, `Then`, `Else`) use the `slots` map
on `ActivityNode`, keyed by the CLR property name of the member.

## Consequences

- The tool does not own the AST format. Callers construct their own generate input; scaffold
  provides guided support, not a mandatory contract.
- `expressionLanguage` is explicit and required in the generate input — the generator never guesses.
- Scaffold output and generate input are co-designed: `ArgumentDescriptor.name` is the key used
  in `ActivityNode.arguments`. Callers do not need to know the catalog schema to use the tool.
- Adding new node kinds (`Flowchart`, `StateMachine`) requires no changes to `Activity` or
  `Sequence` nodes.
