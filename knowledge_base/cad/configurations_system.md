# Configurations System

## Overview

Configurations control parametric families — one Part Studio or Assembly that produces multiple variants. They are the mechanism for part families, size ranges, and configurable designs.

## Two Variable Systems

Onshape has two distinct variable systems. Understanding the difference is critical.

### Parametric Variables

- Exist **only in Part Studios**
- Are features in the feature tree — solved parametrically
- Can only be referenced by features **below them** in the feature tree
- Set with `set_variable` / `get_variables` API calls
- Good for: internal design relationships within a single Part Studio

### Configuration Variables

- Exist in **both Part Studios and Assemblies**
- Are NOT features — they exist "one level above features"
- Control feature variance from outside the feature tree
- This is what makes them powerful for part families — external control
- Good for: parametric families, size ranges, configurable products

## Configuration Input Types

Six available types for configuration inputs:

| Type | UI Element | Use Case |
|------|-----------|----------|
| **Enum** | Dropdown selection | Material choice, size category, style |
| **Boolean** | Checkbox | Include/exclude feature, left/right hand |
| **String** | Text input | Part number prefix, label text |
| **Length** | Dimensional input with units | Width, height, depth, thickness |
| **Angle** | Angular input with units | Rotation, draft angle, sweep angle |
| **Number** | Numeric value | Count, ratio, scale factor |

**NOT supported as configuration input**: Queries (geometry selections). You cannot make a face/edge selection configurable.

### Enum Configuration

Associated with a FeatureScript enum type `<inputId>_conf`. Each enum value can drive different parameter sets.

```
// FeatureScript enum for configuration
export enum size_conf
{
    SMALL,
    MEDIUM,
    LARGE
}
```

## Variable Studios

A dedicated document element for holding variables/parameters centrally:

- Define critical dimensions (material thickness, hole sizes, clearances) in one location
- Can be referenced across multiple Part Studios and Assemblies within the same document
- Enables global parametric control — change one value, update everywhere

**Best practice**: Use Variable Studios for dimensions shared across multiple Part Studios (material thickness, standard clearances, hardware sizes).

## Derived Parts

Pattern for configuration-driven part families:

1. Create a **configurable Part Studio** with configuration variables (the "master")
2. Create a second Part Studio that **derives** the first with specific configuration values
3. Each derived instance gets a specific configuration "baked in"

**Advantages:**
- Avoids version explosion (one master, many derived variants)
- One configurable model generates a set of "standard" parts
- Simplifies revision management — update the master, all derived parts update

## Using Configurations in Assemblies

Configuration inputs created in a Part Studio can be selected when inserting parts into assemblies:

1. Insert part from a configurable Part Studio
2. Select specific configuration values in the insert dialog
3. The assembly references that specific configuration
4. Multiple instances of the same Part Studio can have different configurations

## Configuration API Usage

### Workflow

1. **Get available options**: `GET /elements/.../configuration` — retrieve all configuration parameters and their valid values
2. **Encode selections**: `POST /elements/.../configurationencodings` — encode selected parameter values to a URL-safe string
3. **Use in operations**: Pass the encoded configuration string to export endpoints, instance creation, etc.

### Critical Gotcha

**Changing the configuration changes the Part ID.** The agent must re-query Part IDs after any configuration switch. Do not cache Part IDs across configuration changes.

```python
# After changing configuration, re-query parts
parts_before = api.get_parts(doc, ws, elem)  # Part IDs: ["JHD", "JKD"]
# ... change configuration ...
parts_after = api.get_parts(doc, ws, elem)   # Part IDs may differ: ["JLD", "JMD"]
```

## Lookup Tables

A structured UI for specifying parameters through a decision tree — sub-options within options. More structured than simple enum selection.

Example: Select "Bolt" → then "M3" → then "12mm" → drives all related dimensions automatically.

## Best Practices for Agents

1. **Use configurations for part families** — one parametric Part Studio, multiple configurations, versus duplicating Part Studios
2. **Variable Studios for shared dimensions** — material thickness, clearances, hardware sizes
3. **Re-query Part IDs after config changes** — Part IDs are not stable across configurations
4. **Pre-check configuration count** before iterating — if unexpectedly high, abort to conserve API calls
5. **Derived parts for "standard" variants** — master Part Studio + derived instances for common sizes

## Resources

- [Configurations API Guide](https://onshape-public.github.io/docs/api-adv/configs/)
- [Tech Tip: Parametric vs Configuration Variables](https://www.onshape.com/en/resource-center/tech-tips/tech-tip-parametric-vs-configuration-variables)
- [Tech Tip: Configure Derived Features](https://www.onshape.com/en/resource-center/tech-tips/tech-tip-how-to-configure-derived-features-in-onshape)
