# Assembly Best Practices at Scale

## Document Organization Strategy

For assemblies with 50+ parts, the hierarchical multi-document approach is critical:

```
Top-Level Assembly (Document A)
  |-- Sub-Assembly 1 (Document B, version-locked)
  |     |-- Parts for mechanism 1
  |-- Sub-Assembly 2 (Document C, version-locked)
  |     |-- Parts for mechanism 2
  |-- Purchased Components (Document D, version-locked)
  |     |-- Motor assembly
  |     |-- Fasteners (simplified)
  |-- Integration Assembly (Document A)
        |-- Connects sub-assemblies together
```

### Three-Level Hierarchy

1. **Main assembly** (top-level): Visualize everything together, final export
2. **Integration sub-assemblies**: Where editing happens, mechanism-level groups
3. **Import sub-assemblies**: Where raw imported data comes in (STEP files, vendor models)

### Key Rule: Break Large Designs into Multiple Documents

"It is a best practice to break up a large design into multiple documents...at the very least, link the parts in your assembly to a version instead of the main workspace."

**Why**: When sub-assemblies are in separate documents, changes only regenerate that document's sub-assembly, not the entire assembly tree.

## Part Studio Organization

- Model parts for each major mechanism in a single Part Studio
- Orient all Part Studios to the **same origin** as the top-level assembly
- One Part Studio per mechanism/module
- **One unique part type per Part Studio** — parts with identical bounding dimensions in the same PS can merge (confirmed in our S471 experience)

## Performance Optimization Techniques

### 1. Simplify Fasteners (100x triangle reduction)

Imported fully-threaded fasteners can be 400K triangles. Simplified versions (cylinder approximation) drop to ~4K triangles — a 100x reduction.

**Rule**: Never use detailed fastener models in large assemblies. Use simplified representations.

### 2. Hide Occluded Parts

Hiding invisible sub-assemblies provides ~1.5x frame rate improvement. Use display states or manual hiding for parts inside enclosures, behind panels, etc.

### 3. Use Groups Instead of Mates for Rigid Relationships

Groups define spatial relationships without mate-solving calculations. For non-moving connections, Groups are faster than fastened mates.

"Groups instead of mates as much as possible can help performance, since mates involve calculations."

**When to use Groups**: Parts that never move relative to each other (structural frame, enclosure panels, PCB mounting)

**When to use Mates**: Parts with defined motion (hinges, slides, rotational joints)

### 4. Configuration Suppression

Create simplified configuration checkboxes to suppress non-essential detail:
- Fastener patterns → suppress in "lightweight" config
- Cosmetic features (labels, engravings) → suppress
- Internal detail → suppress when viewing externals

### 5. Version References for Sub-Assemblies

Version references are immutable and static — no automatic updating. This means:
- Less regeneration time
- Faster assembly load times
- No surprise changes from sub-assembly edits

You choose when to update to newer versions manually.

### 6. Practical Limits

"Rarely more than 50 components visible on screen at one time." For larger assemblies, use:
- Display states to show/hide groups
- Sub-assembly isolation (open individual sub-assemblies for editing)
- Level-of-detail settings

## Sub-Assembly Decomposition Rules

### When to Use Sub-Assemblies

- **Reusable modules**: A motor assembly used in 5 locations
- **Independent mechanisms**: A drawer, a hinge assembly, a gear train
- **Purchased components**: Motors, pumps, LCD screens, off-the-shelf parts
- **When assembly exceeds ~50-100 visible parts**
- **When multiple people need to work on different sections**

### When to Keep Flat

- Simple assemblies (<50 parts)
- Non-reusable groupings
- When you need global mate access (sub-assembly mates are internal, not accessible from parent)

### Sub-Assembly Decomposition Checklist

1. **Identify mechanisms**: Each moving mechanism = separate sub-assembly
2. **Identify modules**: Reusable groups of parts = separate sub-assembly
3. **Identify vendors**: Purchased components = separate document, version-locked
4. **Remaining parts**: Integration parts that connect mechanisms = top-level or integration sub-assembly

## Mate Organization

### In Sub-Assemblies

- Mates within sub-assemblies are solved independently
- Fully constrained sub-assemblies become "rigid" in parent — faster solve
- Internal mates are not visible from parent assembly

### At Top Level

- Mate sub-assemblies to each other (not individual parts across sub-assemblies)
- Use fastened mates for rigid connections between sub-assemblies
- Reserve motion mates (revolute, slider) for mechanism joints

### Mate Ordering

1. Ground the reference part first (structural frame, base plate)
2. Mate structural connections (frame members, panels)
3. Mate mechanism joints (hinges, slides)
4. Mate purchased components last (motors, fasteners)

### Critical Rules (from our experience)

- **NEVER use anti-parallel mates** — they flip parts 180° even with grounded reference
- **Same-direction coplanar faces + MC offsets** = reliable mating pattern
- **Delete mates BEFORE repositioning** mated instances — solver cascade will shift entire assembly
- **Deleting a mate does NOT delete its mate connectors** — clean up orphaned MCs separately
- **Create mates in batches of 3-5**, verify between batches with `get_assembly_features` and `get_assembly_positions`

## Performance Panel

Onshape's built-in tool for identifying performance bottlenecks in assemblies. Use it when:
- Assembly takes >5 seconds to load
- Rotating/panning is sluggish
- Mate solving takes too long

## For the Agent

### Assembly Strategy for Complex Builds

1. One Part Studio per mechanism/module
2. Orient all Part Studios to same origin as top-level assembly
3. Use Groups for rigid relationships, Mates only for moving joints
4. Keep <50 visible components on screen
5. Simplify fasteners (use cylinder approximation)
6. Link sub-assemblies to versions, not workspaces
7. Create instances in bulk, then position in bulk, then mate in batches
8. Verify after each batch: `get_assembly_features` (all OK?) + `get_assembly_positions` (correct?)

## Resources

- [Onshape Forum: Large Assembly Management](https://forum.onshape.com/discussion/25749/best-practices-for-managing-large-assemblies)
- [Onshape Help: Performance Tips](https://cad.onshape.com/help/Content/performance)
- [Onshape Help: Assemblies](https://cad.onshape.com/help/Content/assembly)
