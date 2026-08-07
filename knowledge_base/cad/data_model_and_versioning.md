# Onshape Data Model and Version Control

## Core Hierarchy

```
Document (container for all design data)
  |
  |-- Element (tab in the UI)
  |     |-- Part Studio (zero or more parts defined by feature list)
  |     |-- Assembly (parts and sub-assemblies with mate relationships)
  |     |-- Feature Studio (custom FeatureScript definitions)
  |     |-- Blob (uninterpreted binary — PDFs, images)
  |     |-- Application (iframe-based — Drawings are specialized applications)
  |
  |-- Workspace (mutable branch — like git branch)
  |-- Version (immutable named snapshot — like git tag)
  |-- Microversion (individual change — like git commit)
```

## Documents

The top-level container for all design data. Contains one or more Elements (tabs). A new document starts with a single workspace called "Main."

**URL structure**: `https://cad.onshape.com/documents/{documentId}/w/{workspaceId}/e/{elementId}`

**Free plan constraint**: All documents must be `isPublic: true`. Private documents require Professional ($1,500/user/year) or Enterprise.

## Elements (Tabs)

Five types:

| Type | Purpose | API Resource |
|------|---------|-------------|
| Part Studio | Define parts via feature list (sketches, extrudes, etc.) | `/api/v9/partstudios/` |
| Assembly | Combine parts with spatial relationships | `/api/v9/assemblies/` |
| Feature Studio | Custom FeatureScript definitions | N/A (FeatureScript API) |
| Blob | Binary files (PDFs, images, imported CAD) | `/api/v6/blobelements/` |
| Application | Iframe-based (Drawings are this type) | `/api/v6/applications/` |

## Workspaces

A workspace is a **mutable branch** of the document. All changes are applied to workspaces. Every document starts with a workspace called "Main."

"A workspace can be thought of as a sandbox — when you want to try something new, you create a new workspace (on a new branch)."

**API path**: `/d/{documentId}/w/{workspaceId}/e/{elementId}`

Use workspaces for active editing. Use versions for stable references.

## Versions

A **named, immutable snapshot** of the entire document at a specific microversion. "You can never change or edit a version in any way."

**API path**: `/d/{documentId}/v/{versionId}/e/{elementId}`

Use versions for:
- Stable references in assemblies (sub-assembly links)
- Release management (release candidates reference versions)
- Linked documents (cross-document references always point to versions)
- Before experimental work (create a version as a save point)

## Microversions

Individual changes creating a new document state. Each microversion stores a reference to the parent microversion plus the actual definition change. Immutable.

"Whenever the user changes the Part Studio definition, a new one is created to represent this new definition."

**API path**: `/d/{documentId}/m/{microversionId}/e/{elementId}`

Microversions correspond to git commits. Most API interactions use workspaces, not microversions directly.

## Branching and Merging

### Branching

Creating a new workspace from a version. "A branch is not another file or a copy to maintain. Rather, it's a pointer to the original CAD model version."

**Use cases:**
- Experimental design exploration
- Parallel work by multiple designers
- Agent safety: branch before risky operations

### Merging

Merge from a source (version or workspace) into the active target workspace.

**Key behavior**: "If a dimension is modified in two different ways on two workspaces, in a merge, the 'from' workspace will win."

**No merge conflicts**: "Merge conflicts should never happen." This is a fundamental design choice — last write wins per dimension. Unlike git, there is no conflict resolution step.

### Version Safety Pattern (for agents)

Before any experimental work:
1. Create a Version (named snapshot — save point)
2. Create a Branch (new workspace from the version)
3. Do experimental work in the branch
4. If successful → merge back to Main
5. If failed → delete workspace (original version preserved)

## Linked Documents

Cross-document references always point to specific **versions** (immutable).

- Stable reference — never breaks
- You choose when to update to newer versions
- "That document version is preserved as long as any document references it, even if the containing document is deleted"

**Best practice for assemblies**: Link sub-assemblies to versions, not workspaces. Changes to sub-assembly documents only affect the parent assembly when you explicitly update the version reference.

## ID System

| ID Type | Format | Persistence |
|---------|--------|-------------|
| User ID | 24-character string | Permanent |
| Document ID | 24-character string | Permanent |
| Workspace ID | 24-character string | Permanent (within document) |
| Version ID | 24-character string | Permanent |
| Microversion ID | 24-character string | Permanent |
| Element ID | 24-character string | Permanent (within document) |
| Part ID | Variable-length string | **NOT persistent** across sessions/model changes |
| Face ID | Variable-length string | **NOT persistent** — changes with topology |
| Edge ID | Variable-length string | **NOT persistent** — changes with topology |

**Critical for agents**: Part IDs, Face IDs, and Edge IDs are NOT persistent. They change when the model is modified. Always re-query after making changes. Never cache geometry IDs across operations.

## Git Analogy

"This mechanism is similar to (and was inspired by) what the popular software version control system git does, with microversions corresponding to git 'commits' and workspaces corresponding to branches."

### Key Differences from Git

| Concept | Git | Onshape |
|---------|-----|---------|
| Commit | Per-file changes | Microversion (per-document) |
| Branch | File-level | Workspace (document-level) |
| Tag | Annotated point in history | Version (document-wide snapshot) |
| Merge conflicts | Manual resolution required | No conflicts — last write wins |
| Scope | Repository (many files) | Document (many elements) |

## Storage and Performance

- All data stored in replicated cloud databases (not files)
- Tessellated geometry is NOT stored persistently — generated on-demand and cached
- Repeated tessellation requests may be slow on first call
- Version references are immutable and static — less regeneration time, faster assembly loading

## Resources

- [Architecture Documentation](https://onshape-public.github.io/docs/api-intro/architecture/)
- [Document Model Introduction](https://onshape-public.github.io/docs/api-intro/)
- [Branch and Merge](https://www.onshape.com/en/features/branch-merge-cad)
- [Onshape Help: Workspaces](https://cad.onshape.com/help/Content/workspaces.htm)
