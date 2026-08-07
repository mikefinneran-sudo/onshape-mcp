# Manufacturing Workflows

## Design-to-Manufacturing Pipeline

```
Design (Part Studios)
  → Assembly + BOM (auto-generated)
  → Drawing (dimensioned views, annotations, GD&T)
  → Release Candidate (bundle objects)
  → Approval Workflow (approvers + observers)
  → Released Revision (immutable)
  → Export (STEP/PDF/DXF via API or manual)
  → ERP/PLM Integration (BOM data pipeline)
```

## Bill of Materials (BOM)

### Two BOM Views

| View | Structure | Use Case |
|------|-----------|----------|
| **Flattened** | Simple list of all parts from all levels, no hierarchy | Parts ordering, material lists, procurement |
| **Structured** | Parent-child relationships preserved | Manufacturing assembly instructions, work orders |

BOM data updates automatically in real-time as the assembly is designed.

### BOM Behavior Property

Controls manufacturing intent for each component:

| Behavior | Meaning | Example |
|----------|---------|---------|
| **Manufactured** | Standard part to be made | Custom bracket, housing |
| **Purchased** | Bought as a whole assembly | Motor, pump, LCD screen |
| **Phantom** | Grouping container only, not a real part | Logical sub-assembly for organization |
| **Serviceable** | Can be replaced as a unit | Filter cartridge, wear part |

### BOM API

Available for custom apps to:
- Extract BOM table data programmatically
- Export directly to ERP systems
- Automate procurement workflows

### Third-Party Integration

**OpenBOM for Onshape**: Cloud-native BOM management with single-click extraction from Onshape assemblies.

## Drawings

### Drawing Types

Drawings in Onshape are Application-type elements (iframe-based). They provide:

| Feature | Purpose |
|---------|---------|
| **Orthographic views** | Standard 2D projections (front, top, right, isometric) |
| **Section views** | Cut-through views showing internal detail |
| **Detail views** | Zoomed views of specific areas |
| **Dimensions** | Linear, angular, radial, diameter |
| **Annotations** | Notes, symbols, balloon callouts |
| **GD&T** | Geometric dimensioning and tolerancing (datums, feature control frames) |
| **Tables** | BOM tables, hole tables, revision tables |

### 2025-2026 Drawing Improvements

| Date | Feature |
|------|---------|
| Nov 2025 | Dimension inferencing (auto-detect dimension placement) |
| Mar 2026 | MBD (Model-Based Definition) cylinder dimensions |

### Drawing API

Drawings are Application-type elements. The API supports:
- Creating drawing views
- Adding dimensions and annotations
- Exporting to PDF/DXF

## Release Management

### Release Workflow States

```
Pending → Under Review → Released
                      → Rejected (back to Pending)
```

1. **Create Release Candidate**: Select objects (parts, assemblies, drawings, imported files)
2. **Status: Pending**: Awaiting submission
3. **Submit for Approval**: Route to designated approvers
4. **Status: Under Review**: Approvers evaluate the candidate
5. **Approve or Reject**: Approvers decide
6. **Status: Released**: Available for manufacturing (immutable)

### Roles

| Role | Capability |
|------|-----------|
| **Creator** | Submit release candidates; can release immediately (depending on admin config) |
| **Approver** | Required to approve/reject; can be individual, team, or company member |
| **Observer** | Can view release candidate; no approval responsibility |

### Revision Schemes

| Scheme | Example | Notes |
|--------|---------|-------|
| Alphabetical | A, B, C, ... | Most common |
| Numerical | 1, 2, 3, ... | Alternative |
| Custom | Per company rules | Text file upload (minimum 50 lines) |

Auto-numbering available on Professional/Enterprise plans.

### Part Numbering

| Feature | Description |
|---------|-------------|
| Manual assignment | User enters part number |
| Sequential auto-generation | System generates next number |
| Applies to | Release Objects, Standard Content, Items |
| External sync | Can pull from third-party systems via REST API |

### Release Configuration

Enterprise admins can configure:
- Whether approver is required
- Whether all approvers must approve (or just one)
- Whether creator can also be approver
- Whether notes are required
- Auto-obsolete previous revisions
- Error checking (feature list errors, rolled-back, assembly errors, out-of-date refs)

### Releasing Configured Parts

Releasing an Assembly that contains configured parts releases **only the specific configurations referenced by the Assembly**. No additional configurations are released unless explicitly added.

## Export Formats

### Part Studio Exports

| Format | Use Case |
|--------|----------|
| STL | 3D printing, visualization |
| STEP | Interchange with other CAD (most universal) |
| PARASOLID | Native kernel format, highest fidelity |
| GLTF | Web viewers, AR/VR |
| OBJ | Rendering, visualization |

### Assembly Exports

| Format | Use Case |
|--------|----------|
| STL | 3D printing (merged bodies) |
| STEP | Full assembly interchange |
| GLTF | Web viewers with assembly structure |
| SolidWorks | Export for SolidWorks users |

### Export API Pattern

Export is asynchronous:
1. `POST /translations` — initiate export job
2. `GET /translations/{translationId}` — poll status (`ACTIVE` → `DONE` or `FAILED`)
3. Download result from `resultExternalDataIds`

## Workflow Events (Webhooks)

Monitor manufacturing workflow via webhooks:

| Event | Trigger |
|-------|---------|
| `workflow.transition` | Release state change (Pending → Review → Released) |
| `revision.created` | New revision created |
| `model.translation.complete` | Export job finished |

Use these for ERP integration — trigger procurement, work orders, and notifications when releases happen.

## Resources

- [Onshape Release Management](https://www.onshape.com/en/features/release-management)
- [Onshape Bill of Materials](https://www.onshape.com/en/features/bill-of-materials)
- [Dimension Tools in Drawings](https://www.onshape.com/en/resource-center/tech-tips/dimension-tools-onshape-drawings)
- [Export/Translation API Guide](https://onshape-public.github.io/docs/api-adv/translation/)
