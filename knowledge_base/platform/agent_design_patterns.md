# Agent Design Patterns for Onshape

## Two-Interface Architecture

An effective Onshape agent operates through two distinct programmatic interfaces:

### 1. FeatureScript (Inside the Engine)

- Runs inside the Onshape geometry engine
- **Does NOT count against REST API call limits**
- Used for: all geometry creation (sketches, extrudes, booleans, fillets, custom features)
- Used for: geometry evaluation (measurements, bounding boxes, entity queries)
- Executed via: `eval_featurescript` tool or Feature Studio creation

### 2. REST API (External)

- Runs externally via HTTP calls
- **Counts against annual API call limits** (2,500-10,000/year)
- Used for: document management, assembly operations, export, BOM, release management
- Every call must be justified and cached

### Budget Rule

FeatureScript is free. REST API is scarce. The agent should:
- Maximize FeatureScript usage for all modeling operations
- Minimize REST API calls through caching and bulk operations
- Track API usage manually (no built-in usage counter)

## API Call Budget Management

### Free Plan: 2,500 calls/year = ~6.85/day

Every call matters. Strategy:

| Category | Approach | API Cost |
|----------|----------|----------|
| Create document | REST (unavoidable) | 1 call |
| Create Part Studio | REST (unavoidable) | 1 call |
| Create sketch + extrude | FeatureScript | 0 calls |
| Set variables | REST (1 call sets multiple) | 1 call |
| Get parts | REST (cache result) | 1 call |
| Get body details | REST (cache result) | 1 call |
| Create assembly | REST (unavoidable) | 1 call |
| Add instances (bulk) | REST (use transformedinstances) | 1 call |
| Create mates (batch) | REST (one per mate) | N calls |
| Check interference | REST | 1 call |
| Export | REST (initiate + poll) | 2 calls |

### Estimated Cost per Build Type

| Build | Estimated API Calls | Notes |
|-------|-------------------|-------|
| Simple part (1 PS, no assembly) | 5-8 | Create doc + PS + features + verify |
| Simple assembly (5 parts, 1 PS) | 15-20 | + assembly + instances + mates + verify |
| Medium assembly (20 parts, 3 PS) | 40-60 | + multiple PS + more mates |
| Complex assembly (50+ parts, subs) | 80-150 | Sub-assemblies, many mates, exports |

### Optimization Techniques

1. **Cache all GET responses** — never repeat identical calls
2. **Use bulk endpoints** — `POST /assemblies/.../transformedinstances` creates AND positions in one call
3. **Use `POST /assemblies/.../modify`** — batch delete/suppress/transform multiple instances in one call
4. **Batch mate creation** — create 3-5 mates, verify once (not verify after each)
5. **Use FeatureScript for measurements** — `eval_featurescript` for bounding boxes instead of separate API calls

## Version Safety Pattern

Before any experimental or risky work:

```
1. Create a Version (named snapshot — save point)
2. Create a Branch (new workspace from the version)
3. Do experimental work in the branch
4. If successful → merge back to Main workspace
5. If failed → delete workspace (original version preserved)
```

**When to branch:**
- Trying a new assembly strategy
- Large-scale redesign
- Testing configuration changes
- Any operation you might need to undo

**When NOT to branch (save the API calls):**
- Simple, well-understood operations
- Adding a single part or mate
- Export operations

## Assembly Strategy for Complex Builds

### Phase 1: Plan (no API calls)

1. Parse the design requirements
2. Identify all unique parts and their dimensions
3. Plan Part Studio organization (one unique part type per PS)
4. Plan assembly hierarchy (sub-assemblies for mechanisms)
5. Compute all positions mathematically
6. Plan mate sequence

### Phase 2: Create Parts (minimal API calls)

For each Part Studio:
1. Create PS (1 call)
2. Set variables (1 call)
3. Create all features via FeatureScript (0 calls if using eval_featurescript)
4. Verify with get_bounding_box (1 call)
5. Get Part IDs (1 call)

**Total per PS: ~4 calls**

### Phase 3: Assemble (bulk operations)

1. Create assembly (1 call)
2. Add ALL instances with transforms in one call using `transformedinstances` (1 call)
3. Ground reference part (1 call)
4. Get body details for mate planning (1 call per PS)
5. Create mates in batches of 3-5 (N/3 to N/5 verification calls)
6. Final verification: positions + interference (2 calls)

### Phase 4: Export (if needed)

1. Initiate export (1 call)
2. Poll for completion (1-3 calls)

## Configuration-Driven Parametric Design

For part families (multiple sizes/variants):

1. Build ONE configurable Part Studio with configuration variables
2. Use the Configuration API to generate variants
3. Track Part ID changes after configuration switches (Part IDs are NOT stable)
4. Insert specific configurations into assemblies

**Saves API calls**: One Part Studio with configurations vs. N separate Part Studios.

## Error Recovery Patterns

### Feature Creation Failure (409 Conflict)

The feature could not be regenerated. Common causes:
- Invalid sketch geometry (self-intersecting, zero-area)
- Extrude direction creates zero-volume body
- Boolean target/tool don't intersect

**Recovery**: Delete the failed feature, examine the error, adjust parameters, retry.

### Mate Failure

Mate status shows ERROR in `get_assembly_features`.

**Recovery**: Delete the mate and its orphaned mate connectors. Re-examine face IDs, normals, and offsets. Use same-direction coplanar faces (never anti-parallel).

### Position Drift

Parts not where expected after mating.

**Recovery**: Check reference part is still grounded. Verify positions relative to reference (compute `instance_pos - reference_pos`). Delete cascading mates and rebuild in correct order.

## Webhook-Driven Workflows

For automated pipelines:

```
Agent creates design
  → Agent creates release candidate
  → Webhook: workflow.transition (Pending → Review)
  → Human approves
  → Webhook: workflow.transition (Review → Released)
  → Webhook: revision.created
  → Agent triggers STEP export
  → Webhook: model.translation.complete
  → Agent downloads and delivers export
```

## Resources

- [API Call Limits](https://onshape-public.github.io/docs/auth/limits/)
- [Bulk Assembly Operations](https://cad.onshape.com/api/openapi) — search for `modify` and `transformedinstances`
- [Webhook Documentation](https://onshape-public.github.io/docs/app-dev/webhook/)
- [Configuration API](https://onshape-public.github.io/docs/api-adv/configs/)
