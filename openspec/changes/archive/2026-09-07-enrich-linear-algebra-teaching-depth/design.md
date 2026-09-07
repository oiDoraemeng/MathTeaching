# Design: 线性代数数形结合教学规划器

## Context

See `proposal.md` for motivation and scope. The current catalog already provides
54 stable topic IDs and topic-specific builders, while the runtime validates all
scene changes through `SceneCommandService`. The remaining gap is that the
explanation model is a flat Python object and the visual builders receive no
machine-checkable statement of the mathematical claim they are supposed to
show. `common.py` also contains a capability-based hard-coded plan path that can
produce a plausible but irrelevant picture.

The lecture source has irregular heading levels and mixes definitions, proofs,
examples, and exercises in the same section. A source anchor therefore needs a
text fingerprint in addition to a heading path. The application is offline-first
and local, so generated content must be reviewable, versioned, and usable after
restart without another model request.

## Goals / Non-Goals

**Goals:**

- Make a mathematical claim the smallest unit shared by prose, formula,
  example, and visual semantics.
- Define five measurable teaching levels so “deeper explanation” is testable,
  not merely longer.
- Preserve accepted sub-agent replies while keeping executable rendering data
  behind a deterministic compiler.
- Compile semantic relationships into a deterministic storyboard and validated
  `CommandPlan`.
- Load explanation and scene as one topic bundle with rollback on any failure.

**Non-Goals:**

- Do not let the model emit scene operations, code, or renderer objects.
- Do not change the lecture source or expand the first three chapters.
- Do not add a continuous animation timeline. Stages are static snapshots,
  selectable cards, or side-by-side lanes.
- Do not require a remote content service or a runtime model call when a topic
  is opened.

## Decisions

### 1. Use a claim-first teaching artifact

`TeachingArtifact` is the persisted unit for a topic. Its logical shape is:

```text
TeachingArtifact
  source
  teaching_profile
  claims[]
  explanation
  visual_semantics
  generation_receipt
```

Each `Claim` has a stable ID, a student-facing statement, optional formula,
source references, and references to the semantic entities, relations, and
stages that provide visual evidence. The explanation sections reference claim
IDs rather than repeating disconnected prose.

The five teaching levels are:

```text
L0 看见       识别图中的对象和角色
L1 读懂       说清定义、符号和公式
L2 算出       完成可复算的数字例题
L3 解释       说明几何意义、不变量和边界情况
L4 迁移       连接主题、比较变体并识别误解
```

Every topic declares a minimum level and the required sections for that level.
Core and bridge topics reach L3/L4; high-dimensional analogy topics may stop at
L3 but must mark analogy boundaries. This is preferred over a free-form word
count because a short proof can be deeper than a long summary.

Alternatives considered:

- Keep the current flat `ExplanationContent`: rejected because it cannot bind a
  formula variable to a visible object or prove that a picture supports a
  conclusion.
- Store only Markdown: rejected because heading parsing and free-form blocks
  make validation and stable rendering fragile.
- Let the model emit a plan: rejected because it couples untrusted output to
  the scene protocol.

### 2. Make visual semantics a typed mathematical graph

The semantic graph is deliberately not a scene protocol:

```text
Claim -> Entity -> Relation -> Stage -> semantic primitive
```

An entity contains an ID, kind, dimension, mathematical value when needed,
teaching role, label, and claim references. A relation contains an ID, a
controlled relation name, source/target entity IDs, parameters, and claim
references. A stage contains inputs, outputs, relation IDs, expected
invariants, and a presentation slot.

The initial relation vocabulary includes `sum`, `difference`,
`scalar_multiple`, `maps_to`, `spans`, `projects_to`, `orthogonal_to`,
`collapses_to`, `composition_order`, `compare`, `orientation`,
`decomposes_into`, `has_foot`, `has_residual`, `batch_maps_to`,
`endpoint_diff`, `same_measure`, and `invariant`.

Numeric values are finite 2D/3D vectors, matrices with explicit shape, points,
or bounded scalar parameters. Arbitrary expressions, colors, aliases, camera
objects, and executable strings are invalid semantic values.

This allows a validator to answer questions such as:

- Does every symbol in `(AB)x=A(Bx)` have an entity binding?
- Does the `AB != BA` claim reference two distinct paths from the same input?
- Does a projection claim contain a foot, residual, and orthogonality relation?

### 3. Ground claims in source spans, not headings alone

`SourceContext` contains the canonical heading path, heading level, occurrence,
the selected excerpt, neighboring topic titles, and a normalized excerpt hash.
Each claim may additionally reference a bounded source span by text fingerprint
and diagnostic line range. Line numbers are not the identity because the lecture
contains headings with inconsistent levels and later edits can shift lines.

The prompt wraps source text as inert reference material. It explicitly forbids
treating source text as instructions. The agent may derive a calculation from a
formula in the excerpt, but may not introduce a new chapter concept.

### 4. Preserve the accepted reply separately from runtime content

Generation has three states: `draft`, `reviewed`, and `published`.

- A draft keeps the exact accepted JSON reply, source hash, prompt fingerprint,
  provider/model metadata, and validation diagnostics.
- A reviewed artifact contains the normalized deterministic structure plus a
  content digest and review decision.
- A published bundle contains the normalized artifact and an audit reference to
  the exact raw reply. The renderer never reads raw reply text.

Replies that fail safety parsing are not copied into published resources. Only
their digest, error code, and bounded diagnostics are retained. This preserves
the accepted sub-agent response without creating an execution or log-injection
surface.

JSON files remain the source-controlled format because they are diffable and
portable. An index maps `topic_id` to the latest published revision; old
revisions remain addressable for comparison and rollback.

### 5. Compile semantics at publish time and cache by digest

`VisualSemanticsCompiler` is the only boundary that can create a `CommandPlan`.
Publishing compiles the validated semantic graph with a compiler version and a
`RenderContext` profile, checks the resulting plan, and records its plan digest.
Runtime may reuse that deterministic compiled snapshot; if the compiler version
or render profile changes, it recompiles without calling the model.

The compiler performs:

1. semantic schema and reference validation;
2. topic `VisualContract` validation;
3. deterministic coordinates, aliases, layout slots, stage labels, and view
   bounds using the render seed;
4. teaching-role color lookup;
5. translation to existing scene operations;
6. `SceneCommandService` validation and plan hashing.

Unsupported semantics fail with the topic ID and relation name. There is no
“draw a few vectors” fallback.

Alternatives considered:

- Compile only when a user clicks a topic: rejected because first-open latency
  hides content errors and makes a published resource non-deterministic.
- Persist only raw scene commands: rejected because commands become stale when
  the scene protocol evolves and they lose the mathematical source of truth.

### 6. Use a storyboard instead of an animation timeline

`visual_semantics.stages` is a static storyboard. A stage has a title, caption,
visible entities, highlighted relations, expected invariants, and optional
camera/layout hints. The renderer can present stages as:

- a sequence of selectable snapshots for derivations;
- side-by-side lanes for comparisons such as `AB` versus `BA`;
- an overlay for before/after transformations.

Stage controls are presentation state only; they do not change the mathematics
or create new commands. A stage is considered complete only when its required
claim evidence is visible.

### 7. Define visual contracts by mathematical claims

Each topic has a static `VisualContract` with required claims, entities,
relations, semantic primitives, minimum stage count, and invariants. It also
declares which relationships must be visually distinguishable.

Examples:

```text
AB != BA:
  same input + two composition_order paths + endpoint_diff + compare

projection:
  input + projection + foot + residual + orthogonal_to

det = 0:
  nonzero inputs + collapses_to or collinear output + zero area
```

Verification checks the semantic contract before compilation and the actual
operations after compilation. Operation counts alone are never sufficient.

### 8. Bind one topic bundle atomically

The registry resolves `topic_id` to `LessonEntry`, published artifact, visual
contract, and compiled plan. The selection transaction is:

```text
topic_id
  -> resolve bundle
  -> verify source/artifact/contract digests
  -> preview compiled plan
  -> begin scene transaction
  -> apply scene
  -> commit scene and explanation view together
```

If resolution, preview, execution, or content rendering fails, the previous
scene and explanation remain visible. The diagnostic includes `topic_id`, bundle
revision, failing phase, and the relevant claim/relation when available.

### 9. Use a shared palette by teaching role

Semantic entities refer to roles such as `vector_a`, `projection`, `residual`,
`area`, or `neutral`. The compiler, scene adapter, Qt view, and Web payload all
resolve the same role palette. Arbitrary hex colors are not part of the agent
contract. This preserves visual meaning across the entire lecture tree.

## Risks / Trade-offs

- **[Source edits invalidate many artifacts]** -> Store normalized excerpt hashes,
  report `stale_source`, and keep the previous published revision readable.
- **[Model produces plausible but unsupported prose]** -> Require source refs for
  claims, exact numeric checks, and a human review state before publication.
- **[Semantic vocabulary grows too quickly]** -> Add a relation only when a
  required claim cannot be expressed by the current vocabulary; each addition
  needs a compiler mapping and a contract test.
- **[Compiled plans become stale after protocol changes]** -> Include compiler
  and render-profile versions in the plan digest and recompile deterministically.
- **[Dense diagrams overwhelm beginners]** -> Use the teaching profile to limit
  visible entities per stage and emphasize one claim at a time.
- **[Legacy explanation resources remain in use]** -> Read them through an
  adapter, but do not publish a topic without visual semantics and a bundle
  identity.

## Migration Plan

1. Introduce the typed artifact, source context, semantic graph, palette, and
   contract models without changing the current renderer behavior.
2. Add the deterministic compiler and generate golden semantic fixtures for the
   focus topics: projection, transformed grid, `AB`/`BA`, null space, and
   determinant area.
3. Add draft/review/publish storage and migrate legacy explanations through an
   adapter while the old builders remain available for rollback.
4. Publish reviewed artifacts chapter by chapter. Runtime prefers a published
   bundle and falls back to the legacy explanation only for topics explicitly
   marked as migration-pending.
5. Remove the capability-only `_build_plan` path after all 54 topics resolve
   through semantic compilation and the validation command reports complete
   coverage.

Rollback is a resource-level operation: point the index to the previous
published revision or enable the legacy adapter. No lecture source changes are
needed.

## Open Questions

None. The remaining choices are implementation details constrained by the
decisions above.
