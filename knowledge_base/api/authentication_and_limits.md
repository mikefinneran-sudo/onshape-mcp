# Authentication and API Limits

## Authentication Methods

### API Keys (for scripts and automation)

Credentials from the Onshape Developer Portal. Stored in `~/.onshape_client_config.yaml` or environment variables.

```
Authorization: Basic base64(access_key:secret_key)
```

Headers required on every request:
```
Accept: application/json;charset=UTF-8; qs=0.09
Content-Type: application/json;charset=UTF-8; qs=0.09
```

### OAuth2 (for app-store apps and third-party integrations)

```javascript
// Bearer token from OAuth2 flow
Authorization: Bearer {access_token}
```

OAuth2 is for published Onshape App Store applications and custom integrations that need user-level permissions.

## Endpoint Structure

```
Base URL: https://cad.onshape.com/api/v{version}
Enterprise: https://{companyName}.onshape.com/api/v{version}

Path template: /{resource}/d/{documentId}/{wvm}/{wvmId}/e/{elementId}
  - w/ = workspace (mutable, for read/write)
  - v/ = version (immutable, read-only)
  - m/ = microversion (read-only, specific change)
```

All IDs are 24-character strings, EXCEPT geometry IDs (Part, Face, Edge) which are variable-length strings.

### API Versions in Use

| API Version | Resource | Notes |
|-------------|----------|-------|
| v6 | Documents, Variables, Translations (export) | Stable, widely used |
| v9 | Part Studios, Assemblies, Parts | Current standard |
| v10 | Document creation | Latest for doc ops |
| v12 | Assembly operations | Latest, stricter type checking |

Always use the latest available version for each endpoint. The Glassworks API explorer (`cad.onshape.com/glassworks`) has the full catalog.

## Annual API Call Limits (CRITICAL)

Enforced since February 2025. Source: Onshape API Limits page + CADSharp.

| Account Type | Annual Limit |
|---|---|
| Enterprise / Enterprise GOV | 10,000 per full user |
| Professional | 5,000 per user |
| EDU Student / Free / Standard | 2,500 per user |
| EDU Enterprise | 10,000 per enterprise |

### What Counts Against the Limit

- API key authenticated calls returning 2xx or 3xx
- Private OAuth2 app calls returning 2xx or 3xx

### What Does NOT Count

- Public App Store apps (via OAuth2)
- Browser/mobile client usage
- Webhook notifications received
- Calls returning 4xx or 5xx errors
- FeatureScript execution (runs inside the engine)

### When Limit Is Exceeded

HTTP **402** response code. Must purchase additional API calls.

### Per-Endpoint Rate Limits

Specific values not published. Trigger HTTP **429** when exceeded. Check `X-Rate-Limit-Remaining` response header for current status.

### The Math for Free Plan

2,500 calls/year = **~6.85 calls/day**. An autonomous agent MUST be extremely efficient.

## Optimization Strategies for Agents

### 1. Cache Aggressively

Retrieve data once, reuse. Never repeat identical calls.

```python
# Bad — calls API every time
for part in assembly_parts:
    details = api.get_body_details(part)  # N calls

# Good — one call, cache result
all_body_details = api.get_body_details(part_studio)  # 1 call
for part in all_body_details:
    # use cached data
```

### 2. Avoid Loops Over Parts

"Avoid API calls in 'simple' loops that run on every assembly part, configuration, custom property." Use bulk endpoints instead.

### 3. Use Bulk Endpoints

- Query entire assemblies vs. individual sub-assemblies for BOM data
- Use Part Studio endpoints to get all parts at once, not individual part endpoints
- Use `POST /assemblies/.../modify` for batch transforms (delete, suppress, transform multiple instances in one call)
- Use `POST /assemblies/.../transformedinstances` to create AND position instances in one call

### 4. Pre-Check Configurations

Before iterating over configurations, check the count first. If unexpectedly high, abort.

### 5. Track Usage Manually

There is no documented way to see current API usage. You must track it yourself.

### 6. Use FeatureScript for Geometry

FeatureScript runs inside the Onshape engine and does NOT count against API limits. Use it for:
- All geometry creation (sketches, extrudes, booleans, fillets)
- Geometry evaluation (measurements, bounding boxes)
- Custom feature definitions

Reserve REST API calls for:
- Document management (create, list, search)
- Assembly operations (instances, mates, transforms)
- Export (STL, STEP, GLTF)
- BOM and release management

## Webhook Events

Comprehensive event system for automation. HTTPS required (CA-signed certificates only; self-signed rejected).

### Event Types

**Document events:**
- `comment.create`, `comment.delete`, `comment.update`
- `document.lifecycle.created`, `document.lifecycle.shared`, `document.lifecycle.statechange`

**Model events:**
- `model.lifecycle.changed` — any model change
- `model.lifecycle.createelement`, `model.lifecycle.createversion`, `model.lifecycle.createworkspace`
- `model.lifecycle.deleteelement`
- `model.lifecycle.metadata` — metadata changes
- `model.lifecycle.changed.externalreferences` — linked document changes
- `model.translation.complete` — export job finished

**Workflow events:**
- `workflow.transition` — release state changes (Pending → Review → Released)
- `revision.created` — new revision created

### Configuration

| Setting | Purpose |
|---------|---------|
| `collapseEvents: true` | Consolidates rapid events into single notification |
| `isTransient: false` | Prevents auto-cleanup after inactivity |

Registration validated via async `webhook.register` trial notification requiring HTTP 200 response.

## Available Client Libraries

### Official (archived)

`onshape-public/onshape-clients` on GitHub — Python, NodeJS, Java, C# samples. Repository archived; replacement status unclear.

### Community

| Library | Language | Status | Notes |
|---------|----------|--------|-------|
| OnPy (`kyle-tennison/onpy`) | Python | Archived Jan 2026 | High-level, sketch+extrude support |
| onshape-robotics-toolkit | Python | Active | Robotics-focused |
| onshape-rest-api-client | Python | Active | Generated from OpenAPI spec |

### Recommendation for Agents

Use direct HTTP calls (httpx/requests) with the Onshape API. The official client is archived and community wrappers have limited scope. The MCP server already implements this pattern.

## Common API Pitfalls

1. **Annual limit exhaustion**: No visibility into current usage; track manually
2. **Configuration ID changes**: Changing configuration changes the Part ID — re-query after config switches
3. **Tessellation not stored**: Generated on-demand and cached; repeated requests may be slow
4. **Part IDs not persistent**: Part IDs change across sessions and model changes
5. **Geometry IDs variable length**: Unlike 24-char document IDs, geometry IDs (Part, Face, Edge) are variable-length
6. **Rate limit headers**: Check `X-Rate-Limit-Remaining` to avoid 429s
7. **Error responses**: 401 (auth), 404 (not found), 409 (conflict/rebuild failed), 402 (annual limit exceeded), 429 (rate limited)

## Resources

- [API Introduction](https://onshape-public.github.io/docs/api-intro/)
- [API Limits](https://onshape-public.github.io/docs/auth/limits/)
- [Glassworks API Explorer](https://cad.onshape.com/glassworks)
- [Webhook Documentation](https://onshape-public.github.io/docs/app-dev/webhook/)
- [CADSharp: Navigating API Limits](https://www.cadsharp.com/blog/onshape-api-rate-limits/)
- [SmartBench: API Limit Tips](https://www.smartbenchsoftware.com/post/navigating-onshape-api-limits)
