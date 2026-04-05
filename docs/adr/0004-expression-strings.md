# ADR-0004: Expression Strings and XAML Serialisation

**Status**: Accepted

## Context

Activity arguments in UiPath Studio XAML are either runtime expressions (VB or C# code evaluated
by the workflow engine) or direct values processed by a TypeConverter at design time. The
generator must know which form to emit for each argument, and how to embed the caller-supplied
value correctly in XAML. This ADR documents the confirmed rules, derived from real
Studio-produced XAML (`InitAllSettings.xaml`, REFramework v25.0.0).

## Decision

### Expression language

Declared once per generate input document as `expressionLanguage` (sourced from UiPath
`project.json` → `design.expressionLanguage`). Applies to all argument values in the document.

| Value | Runtime wrapper | Reference wrapper |
|---|---|---|
| `VisualBasic` | `VisualBasicValue<T>` | `VisualBasicReference<T>` |
| `CSharp` | `CSharpValue<T>` | `CSharpReference<T>` |

### What the caller supplies in the generate input

The caller always supplies a **plain expression string** — raw VB or C# code with no XAML
syntax and no `[...]` brackets. The generator is responsible for all XAML serialisation concerns:
bracket insertion, XML escaping, element wrapping.

```json
"arguments": {
  "Level":   "Trace",
  "Message": "\"Initializing settings...\""
}
```

### Serialisation form: typeConverter present

Source: catalog `member.typeConverter` is non-null (e.g. `"UiPath.Core.Activities.LogLevelConverter"`).

The argument serialises as an **XML attribute** with the raw value passed directly to the TypeConverter.
No `[...]` brackets. No expression evaluator involved.

```xml
<ui:LogMessage Level="Trace" ... />
```

The caller supplies the unqualified enum member name or converter-accepted string: `"Trace"`, not
`"LogLevel.Trace"` and not `"[Trace]"`.

Scaffold output `enumValues` for typeConverter-based enums therefore lists **unqualified** member
names: `["Trace", "Info", "Warn", "Error", "Fatal"]`.

### Serialisation form: typeConverter null (In argument)

Source: catalog `member.typeConverter` is null; `member.dataType` is `System.Activities.InArgument<T>`.

The argument serialises as an **XML attribute** with the expression wrapped in `[...]` brackets.
XML special characters in the expression are escaped.

```xml
<ui:LogMessage Message="[&quot;Initializing settings...&quot;]" ... />
```

The generator:
1. Takes the caller's expression string: `"Initializing settings..."` (VB string literal)
2. Wraps in brackets: `["Initializing settings..."]`
3. XML-encodes for attribute context: `[&quot;Initializing settings...&quot;]`

The caller never includes brackets or XML escaping — that is the generator's job.

### Serialisation form: Out arguments

Out arguments always use **child element form** regardless of typeConverter. The variable name
is wrapped in `[...]` as a location expression.

```xml
<ui:GetRobotAsset.Value>
  <OutArgument x:TypeArguments="x:Object">[AssetValue]</OutArgument>
</ui:GetRobotAsset.Value>
```

The caller supplies the variable name as a plain string: `"AssetValue"`. The generator wraps it
in `<OutArgument x:TypeArguments="...">` and adds brackets.

The `x:TypeArguments` value is derived from the inner type of the catalog `member.dataType`
(e.g. `System.Activities.OutArgument<System.Object>` → `x:Object` using namespace mappings).

### Unset optional arguments

Optional arguments not present in the generate input `arguments` map are omitted from the XAML
output entirely, or emitted as empty elements when required by the activity:

```xml
<ui:GetRobotAsset.TimeoutMS>
  <InArgument x:TypeArguments="x:Int32" />
</ui:GetRobotAsset.TimeoutMS>
```

The generator determines the correct handling per activity from the catalog.

### Null values

Null references serialise as `{x:Null}` in attribute position, or `<x:Null />` in element position.
Example: `CurrentIndex="{x:Null}"` on `ForEach`.

### Variable declarations

Variables scoped to a `Sequence` are declared in `Sequence.Variables`:

```xml
<Sequence.Variables>
  <Variable x:TypeArguments="sd:DataTable" Name="dt_SettingsAndConstants" />
</Sequence.Variables>
```

`x:TypeArguments` is the CLR type resolved to an XML namespace prefix via `namespaceMappings`.
The generate input `SequenceNode.variables` (see issue #19) will carry `name` and `dataType`
(CLR type string); the generator maps the type to the correct `x:TypeArguments` value.

### Workflow-level arguments (full-file mode)

In full-file mode, workflow public arguments are declared as `x:Members`:

```xml
<x:Members>
  <x:Property Name="in_ConfigFile" Type="InArgument(x:String)" />
  <x:Property Name="out_Config"    Type="OutArgument(scg:Dictionary(x:String, x:Object))" />
</x:Members>
```

These correspond to `WorkflowEntry`-level argument declarations in the generate input (not yet
modelled — tracked separately).

## Consequences

- The caller never writes XAML syntax. Expression strings are plain VB/C# code fragments.
- The generator owns all bracket insertion, XML escaping, and element wrapping.
- Enum values for typeConverter-based arguments are unqualified member names (e.g. `"Trace"`,
  not `"LogLevel.Trace"`). The scaffold output `enumValues` field reflects this.
- `typeConverter` presence/absence in the catalog is the sole signal for attribute vs. child
  element serialisation form for In arguments. Out arguments always use child element form.
- `expressionLanguage` from `project.json` is a required input to the generate step; it
  must not be inferred by the generator.
