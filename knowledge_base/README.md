# Onshape MCP Knowledge Base

Comprehensive documentation for training AI agents (Claude Code) that understand the Onshape platform, REST API, FeatureScript, and professional CAD practices.

## Structure

```
knowledge_base/
├── api/                              # Onshape REST API documentation
│   ├── onshape_api_overview.md       # Endpoints, feature JSON, parameter types, variables
│   ├── authentication_and_limits.md  # Auth methods, annual limits (CRITICAL), rate limits, webhooks
│   ├── sketch_creation_guide.md      # BTMSketch-151 format and best practices
│   ├── feature_creation_research.md  # Feature JSON structure reference
│   └── real_sketch_example.json      # Real Onshape sketch example
├── cad/                              # CAD principles and domain knowledge
│   ├── cad_best_practices.md         # Parametric design, feature organization, DFM
│   ├── featurescript_guide.md        # Language, queries, operations, debugging, 2025 updates
│   ├── assembly_at_scale.md          # 100+ part assemblies, sub-assembly strategy, performance
│   ├── configurations_system.md      # Config inputs, variable types, derived parts, API usage
│   ├── data_model_and_versioning.md  # Documents, workspaces, versions, branching, ID system
│   └── manufacturing_workflows.md    # BOMs, drawings, release management, export pipeline
├── platform/                         # Platform-level knowledge
│   ├── competitive_landscape.md      # vs SolidWorks, Fusion 360, FreeCAD, CATIA, Creo
│   └── agent_design_patterns.md      # Two-interface architecture, API budgeting, safety patterns
├── examples/                         # Real-world design examples
│   └── parametric_bracket.md         # Complete L-bracket design walkthrough
├── assembly_workflow_guide.md        # 5-step assembly methodology with gotchas
└── README.md                         # This file
```

## Content Summary

### API Layer (5 files)

| File | Covers | Agent Use |
|------|--------|-----------|
| `onshape_api_overview.md` | Endpoints, feature JSON, parameter types, standard planes | API call construction |
| `authentication_and_limits.md` | OAuth2, API keys, **annual limits (2,500-10,000/yr)**, webhooks | Call budgeting (CRITICAL) |
| `sketch_creation_guide.md` | BTMSketch-151 format, constraint types | Sketch feature building |
| `feature_creation_research.md` | Feature JSON structure, parameter encoding | Feature construction |
| `real_sketch_example.json` | Raw Onshape sketch payload | Reference |

### CAD Domain (6 files)

| File | Covers | Agent Use |
|------|--------|-----------|
| `cad_best_practices.md` | Parametric design, naming, DFM, material-specific rules | Design decisions |
| `featurescript_guide.md` | Language architecture, queries, ops, debugging, community features | Geometry creation |
| `assembly_at_scale.md` | Multi-document strategy, Groups vs Mates, fastener simplification | Large assembly management |
| `configurations_system.md` | 6 input types, Variable Studios, derived parts, Part ID gotcha | Parametric families |
| `data_model_and_versioning.md` | Documents, workspaces, versions, branching, Git analogy | Version control |
| `manufacturing_workflows.md` | BOMs, drawings, release management, export pipeline | Manufacturing prep |

### Platform (2 files)

| File | Covers | Agent Use |
|------|--------|-----------|
| `competitive_landscape.md` | Comparison vs 5 competitors, migration paths | Recommendations |
| `agent_design_patterns.md` | Two-interface architecture, API budgeting, safety patterns | Agent behavior |

### Examples (1 file)

| File | Covers | Agent Use |
|------|--------|-----------|
| `parametric_bracket.md` | Complete L-bracket with variables, feature sequence, DFM | Template |

## Key Facts for Agent Training

### The Two-Interface Rule
- **FeatureScript** = free (runs inside engine, no API cost). Use for ALL geometry.
- **REST API** = scarce (2,500-10,000 calls/year). Use only for document ops, assembly, export.

### Critical Gotchas (from production experience)
- Anti-parallel mates ALWAYS flip parts — use same-direction coplanar faces
- Face IDs belong to Part IDs, not instance names — always verify mapping
- Same-dimension parts in same Part Studio can merge — use separate PSes
- Part IDs change when configuration changes — re-query after config switch
- `set_instance_position` resets rotation to identity
- Front plane extrudes go in -Y direction
- Free plan requires `isPublic: true` on all documents

### Research Sources
This KB was built from:
- Onshape official documentation (developer docs, help content, FeatureScript docs)
- Onshape REST API OpenAPI spec (Glassworks explorer)
- CADSharp blog (2025 enhancements, API limit guidance)
- Onshape community forums (assembly optimization, FeatureScript patterns)
- dcowden/featurescript GitHub (95 community custom features)
- FRC Design community (robotics FeatureScripts)
- Production MCP server experience (Sessions 467-474)

## RAG Integration

For semantic search over the full KB:

```python
from sentence_transformers import SentenceTransformer
import faiss

# Index all .md files → FAISS vector store
# Agent queries KB by semantic similarity
```

## Maintenance

- **On Onshape release notes**: Update affected docs, add new capabilities
- **On MCP tool additions**: Update `onshape_api_overview.md` with new endpoints
- **On gotcha discoveries**: Add to relevant doc + `agent_design_patterns.md`
- **Quarterly**: Review for accuracy against current Onshape behavior
