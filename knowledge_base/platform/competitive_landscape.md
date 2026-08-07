# Competitive Landscape

## Onshape vs Competitors for Programmatic CAD

| Dimension | Onshape | SolidWorks | Fusion 360 | FreeCAD | CATIA | Creo |
|-----------|---------|------------|------------|---------|-------|------|
| **Deployment** | Cloud-native, browser-based | Desktop install | Desktop + cloud | Desktop install | Desktop install | Desktop install |
| **API Type** | REST (HTTP, any language) | COM/VBA (Windows) | TypeScript sandbox (cloud) + Python/C++ (local) | Python scripting | Automation API | Pro/TOOLKIT, J-Link |
| **Language** | Any HTTP-capable (Python, JS, Go, Rust) | VBA, C#, C++ (Windows) | TypeScript (cloud), Python (local) | Python only | VBA, C++ | C, Java |
| **Install Required** | No — agent runs anywhere | Yes | Yes (or cloud sandbox) | Yes | Yes | Yes |
| **Internal Modeling Language** | FeatureScript (same power as built-in features) | Macros (external) | None | Python Part module | Knowledge scripting | Pro/PROGRAM |
| **Version Control** | Built-in (Git-like branching/merging) | PDM/vault (external) | Manual versioning | External (git for files) | ENOVIA PLM | Windchill |
| **Real-time Collaboration** | Multiple simultaneous editors | PDM check-in/check-out | Limited concurrent | None | ENOVIA collab | Windchill |
| **CAM/Simulation** | Third-party only (App Store) | CAM add-on, Simulation | Built-in CAM + FEA | Community FEM + CAM | Built-in (full suite) | Built-in |
| **Open Source** | Standard Library source viewable | No | No | Fully open source | No | No |
| **Large Assembly** | Cloud performance, LOD | Desktop power (stronger) | Cloud + desktop hybrid | Limited | Best in class | Strong |
| **Pricing** | Free (public only), Pro ~$1,500/yr | ~$4,000/yr + PDM | Free (limited), ~$545/yr | Free | Enterprise pricing | Enterprise pricing |

## Why Onshape Wins for Agent-Driven Design

1. **Cloud-native REST API**: No local CAD installation. Agent can run on any server, VM, or CI/CD pipeline. This is the single biggest differentiator.

2. **FeatureScript runs inside the engine**: Custom features with same power as built-in features. Agent can define new feature types that execute inside Onshape's geometry kernel — not as external scripts.

3. **Immutable versions**: Every change tracked, every state recoverable. Safe for agent experimentation via branching. No risk of corrupting the main design.

4. **Webhook automation**: Event-driven workflows without polling. Release management, export completion, and model changes trigger notifications.

5. **Document-level collaboration**: Multiple agents/users can work on different elements simultaneously.

6. **Neutral format imports**: STEP, IGES, Parasolid, SolidWorks, CATIA, Creo, NX files can all be imported directly.

## Real Limitations of Onshape

1. **No native CAM/simulation**: Must use third-party extensions (extra cost, API complexity). For manufacturing-heavy workflows, this is a gap.

2. **Annual API limits**: 2,500-10,000 calls/year depending on plan. This severely constrains high-frequency automation. An agent on the free plan gets ~6.85 API calls/day.

3. **Free plan = public only**: All documents are visible to anyone. Private documents require Professional (~$1,500/user/year) or Enterprise.

4. **FeatureScript not for heavy computation**: FeatureScript is designed for geometry operations, not general-purpose computing. It has execution time limits.

5. **No offline mode**: 100% cloud. No internet = no CAD. For agents, this means network dependency.

6. **Part ID instability**: Part IDs change across sessions and model changes. Agent must re-query frequently.

7. **Desktop performance gap**: For massive assemblies (1000+ parts), desktop CAD (SolidWorks, CATIA, Creo) with dedicated GPU still outperforms cloud rendering.

## When to Choose Each Platform

| Scenario | Best Choice | Why |
|----------|------------|-----|
| Agent-driven automation | **Onshape** | REST API, no install, FeatureScript |
| Manufacturing shop (CAM needed) | Fusion 360 or SolidWorks | Built-in CAM |
| Very large assemblies (1000+ parts) | CATIA or Creo | Desktop power, proven at scale |
| Zero-cost local automation | FreeCAD | Free, Python scripting, no limits |
| Windows-only automation (existing infra) | SolidWorks | COM API, mature ecosystem |
| Enterprise PLM integration | CATIA + ENOVIA or Creo + Windchill | Full PLM suite |
| Team collaboration on design | **Onshape** | Real-time multi-user, built-in PDM |

## SolidWorks Migration Path

SolidWorks is the most common migration source for Onshape. Key considerations:
- Onshape imports SolidWorks files directly (.sldprt, .sldasm, .slddrw)
- Feature history is NOT preserved — import creates "imported" bodies
- Mates must be recreated
- Drawings need to be recreated from scratch
- Macros/VBA must be rewritten (FeatureScript or REST API)

## Fusion 360 Migration

- Import via STEP or direct Fusion file import
- Feature history not preserved
- CAM toolpaths do not transfer (Onshape uses third-party CAM)
- Fusion's timeline-based parametric model is similar conceptually to Onshape's feature tree

## Resources

- [GoEngineer: Onshape vs SolidWorks](https://www.goengineer.com/blog/onshape-vs-solidworks-the-complete-story)
- [Onshape Import Capabilities](https://www.onshape.com/en/features/integrations)
