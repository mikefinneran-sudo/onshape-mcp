# FeatureScript Language Guide

## What FeatureScript Is

FeatureScript is Onshape's built-in programming language for 3D parametric modeling. It is the same language Onshape's developers use to build the platform's core features (Extrude, Fillet, Helix, etc.). Custom features written in FeatureScript have the same power as built-in features.

The Onshape Standard Library is open-source, viewable in a public document named "std". All Standard Library functions are imported by default into new Feature Studios.

**Key advantage for agents**: FeatureScript runs inside the Onshape geometry engine. It does NOT count against REST API call limits. Use FeatureScript for all geometry creation to conserve API budget.

## Architecture and Execution Model

### Context

A built-in structure storing all modeling data: bodies, entities (faces, edges, vertices), variables, and feature error states. All features and operations require a context.

### Entities

Faces, edges, vertices, and bodies. Every face, edge, and vertex belongs to a body.

### Body Types

| Type | Dimension | Description |
|------|-----------|-------------|
| Solid | 3D | Enclosed volume |
| Sheet | 2D | Surface without volume |
| Wire | 1D | Curves/edges |
| Point | 0D | Individual points |

Bodies are always connected — disjoint volumes cannot form a single body.

### Operations (`op*` functions)

Create or modify geometry. Signature: `opFunction(Context, Id, map)`.

| Operation | Purpose |
|-----------|---------|
| `opExtrude` | Extrude sketch regions |
| `opRevolve` | Revolve around axis |
| `opFillet` | Round edges |
| `opChamfer` | Bevel edges |
| `opBoolean` | Union/subtract/intersect bodies |
| `opThicken` | Thicken surfaces |
| `opDraft` | Add draft angles |
| `opSweep` | Sweep along path |
| `opLoft` | Loft between profiles |
| `opPattern` | Linear/circular patterns |
| `opDeleteBodies` | Remove bodies from context |

### Evaluation Functions (`ev*`)

Measure geometry without modifying it. Signature: `evFunction(Context, map)`.

| Function | Returns |
|----------|---------|
| `evBox3d` | Bounding box |
| `evVolume` | Volume of solid |
| `evArea` | Surface area |
| `evVertexPoint` | Point coordinates |
| `evEdgeTangentLine` | Tangent at point on edge |
| `evFaceTangentPlane` | Tangent plane at point on face |
| `evDistance` | Distance between entities |
| `evLength` | Edge/curve length |

### Primitives (`f*`)

Elementary shape creators for common geometries:
- `fCuboid` — rectangular box
- `fCylinder` — cylinder
- `fSphere` — sphere
- `fCone` — cone

## Query System

Queries encode criteria for finding topological entities **without directly referencing them**. This is a key architectural concept — queries are robust to upstream feature changes.

### Two Query Types

1. **State-based queries**: Select entities based on current model state (e.g., "all edges adjacent to a cylindrical face")
2. **Historical queries**: Select entities based on model history (e.g., `qCreatedBy(Id)` — geometry from specific operations)

### Key Query Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `qCreatedBy(Id)` | Geometry from specific operation | `qCreatedBy(id + "extrude1")` |
| `qEverything(EntityType)` | All entities of a type | `qEverything(EntityType.EDGE)` |
| `qContainsPoint(Query, Vector)` | Geometry touching a point | Find face at coordinates |
| `qBodyType(Query, BodyType)` | Filter by body type | `qBodyType(qEverything(), BodyType.SOLID)` |
| `qCapEntity(Id, CapType)` | Cap faces of extrudes | `qCapEntity(id + "ext1", CapType.START)` |
| `qSketchRegion(Id)` | Sketch region reference | `qSketchRegion(id + "sketch1")` |
| `evaluateQuery(Context, Query)` | Resolve to transient queries | Returns array of matching entities |

### Critical Pattern: Boolean Operations

Filter tool queries to `EntityType.BODY` and/or `BodyType.Solid` to avoid ambiguity:

```
// Good — specific body selection
opBoolean(context, id + "boolean1", {
    "tools" : qBodyType(qCreatedBy(id + "extrude2"), BodyType.SOLID),
    "targets" : qBodyType(qCreatedBy(id + "extrude1"), BodyType.SOLID),
    "operationType" : BooleanOperationType.SUBTRACTION
});
```

### Entity Tracking

Use `startTracking` before operations that may change entities (boolean, fillet):

```
var trackedFace = startTracking(context, qCapEntity(id + "extrude1", CapType.END));
// ... perform boolean ...
// trackedFace now resolves to the correct entity post-boolean
```

## Defining Custom Features

### Feature Studio

Custom features are written in Feature Studios (a document element type, like Part Studio or Assembly). Create one via the "+" tab button in any document.

### Feature Structure

```
FeatureScript 2140;  // Standard Library version
import(path : "onshape/std/common.fs", version : "2140.0");

annotation { "Feature Type Name" : "My Custom Feature" }
export const myCustomFeature = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        // UI parameter definitions
        annotation { "Name" : "Depth" }
        isLength(definition.depth, LENGTH_BOUNDS);

        annotation { "Name" : "Faces to select" }
        definition.faces is Query;
    }
    {
        // Feature body — geometry operations
        opExtrude(context, id + "extrude1", {
                "entities" : definition.faces,
                "direction" : evOwnerSketchPlane(context, { "entity" : definition.faces }).normal,
                "endBound" : BoundingType.BLIND,
                "endDepth" : definition.depth
        });
    });
```

### UI Parameter Annotations

| Annotation | Type | Purpose |
|-----------|------|---------|
| `isLength(def.param, BOUNDS)` | Length input | Dimensional value with units |
| `isAngle(def.param, BOUNDS)` | Angle input | Angular value |
| `isInteger(def.param, BOUNDS)` | Integer input | Count/quantity |
| `definition.param is boolean` | Checkbox | Toggle |
| `definition.param is Query` | Selection | Geometry picker |
| `definition.param is string` | Text input | Free text |

### Precondition vs Body

- **Precondition block**: Defines the UI. Runs in the "analysis phase" (while user configures).
- **Body block**: Performs geometry operations. Runs in the "execution phase" (when feature is applied).

## Debugging Techniques

### Analysis Phase (runs continuously as you type)

- Parse errors for grammar violations
- Semantic warnings for undefined variables/functions
- Precondition analysis warnings for feature UI issues

### Execution Debugging (runs in Part Studio)

| Function | Purpose |
|----------|---------|
| `print(value)` | Print to Notices pane (no newline) |
| `println(value)` | Print with newline |
| `printTimer(message)` | Print elapsed time |
| `debug(context, entities)` | Highlight geometry in 3D viewport |

**Notices pane filters**: `:text` (string match), `:elementid`, `:tabname`, `:minlevel`

**Monitoring**: Enable "Monitor [Part Studio name]" for real-time feedback while editing in Feature Studio.

### Performance Profiling

- Hoverable markers showing execution timings >0.1ms
- Color coding: red = longer, yellow = shorter
- Call counts and total time per step
- Warning when exceeding 600 imported modules

### Best Practice

Use the community "Report" FeatureScript instead of raw `println` — provides importance levels (info, debug, warn) and keyed messages for better output control.

## 2025 Enhancements

Major additions to the Standard Library (source: CADSharp, Jan 2025):

| Version | Feature | Impact |
|---------|---------|--------|
| v1.203 | **Query Variables** (`setQueryVariable`) | Features can select geometry created during execution — "a game-changer" |
| v1.193 | **Sheet Metal Forms** | New class of sheet metal modeling |
| v1.195 | **Routing Curves** | 3D wire and tubing creation |
| v1.195 | **Constrained Surfaces** | Surface generation from meshes/point clouds |
| v1.195 | **Cosmetic Threads** | Programmatic thread creation |
| v1.198 | `replaceFace` multi-select | Multiple face selections in one call |
| v1.194 | `opWrap` conical support | Wrapping on conical faces |
| v1.207 | Custom warning messages | `reportFeatureWarning` with custom text |
| v1.206 | Performance improvements | Faster FS editing and execution |

## Community FeatureScripts

From the curated repository (~95 custom features at github.com/dcowden/featurescript) and the FRC community:

### Joinery (furniture/enclosures)

Box/Dovetail Joint, Butt Joint with Pin, Dogbone and Overcut, Kerf Compensation, Laser Joint, Lap Joint, Mortise and Tenon, Rabbet Joint, Snap Hook, T-slot Joint

### Surfaces/Curves/Geometry (advanced modeling)

NACA Airfoil, Parametric Curve, Parametric Surface, Variable Section Sweep, Flex FS, 3D Spline, Contour Spiral, Sculpt Face

### Manufacturing/3D Printing

Hex Infill, Lighten, Part Draft, Pocket Holes, Round Emboss

### Notable Community Features

- **Origin Cube**: Creates origin references + design constants for assembly mating
- **Belt & Chain Gen**: Auto-calculates pulley/sprocket specs from sketch dimensions
- **Tube Converter**: Converts extrusions into punched tube patterns
- **Part Lighten**: Enhanced rib/cut/fillet with weight savings estimates

### Marketplace

**fs.place** — search, purchase, and access custom features with demo documents.

## Resources

- [FeatureScript Language Reference](https://cad.onshape.com/FsDoc/index.html)
- [Standard Library Documentation](https://cad.onshape.com/FsDoc/library.html)
- [Standard Library Source Code](https://cad.onshape.com/documents/12312312345abcabcabcdeff) (public "std" document)
- [Defining Feature Types](https://cad.onshape.com/FsDoc/feature-types.html)
- [Feature UI](https://cad.onshape.com/FsDoc/uispec.html)
- [Debugging in Feature Studios](https://cad.onshape.com/FsDoc/debugging-in-feature-studios.html)
- [Modeling Operations](https://cad.onshape.com/FsDoc/modeling.html)
- [Community FeatureScripts (GitHub)](https://github.com/dcowden/featurescript)
- [FRC FeatureScripts](https://www.frcdesign.org/resources/featurescripts/)
- [2025 FS Enhancements (CADSharp)](https://www.cadsharp.com/blog/2025-onshape-featurescript-onshape-api-enhancements/)
