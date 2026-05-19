# ADR-0002: Use CV-Derived Surface Weight Samples

Status: Proposed
Date: 2026-05-19
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_feather_ribbon_01` builds its sliding surface from an upper anchor edge and a lower anchor-end edge. Those edges can have different segment lengths because a wing can widen toward the lower edge.

The surface U values keep existing guide semantics, but skin weights were previously evaluated from the upper-edge U field only. That made lower-edge CVs inherit anchor and curl weights from a parameter field that did not necessarily match the generated CV positions.

The previous implementation also mixed anchor and curl composition across multiple helper functions: anchor weights were reduced by curl strength inside the anchor helper, and curl raw distribution was recomputed in separate paths.

## Decision

Surface skin weights will be evaluated from each CV's generated world-space position:

- Surface topology and guide-facing U semantics remain upper-edge based.
- Each CV is projected back onto the closest ribbon span patch to recover `span`, `local`, and `depth`.
- Anchor weights are generated from a compact three-anchor neighborhood around the recovered surface distance.
- Surface curl centers are evaluated in the same CV-derived distance field.
- Anchor and curl fields are composed in one place as `anchor * (1 - curl_strength) + curl * curl_strength`.
- The maximum curl contribution is named as `surface_curl_max_weight`.

## Considered Options

1. Keep upper-edge-only skin weights
   - Pros: minimal change and preserves previous weight values.
   - Cons: lower-edge weights drift when the wing widens or narrows.
2. Reparameterize the entire surface and guide U field by depth-aware distance
   - Pros: makes all U consumers distance-aware.
   - Cons: changes row ranges, detail placement, and guide semantics.
3. Keep guide U semantics and reinterpret U by depth only for surface skin weights
   - Pros: accounts for lower-edge length differences.
   - Cons: decouples skin weights from the actual CV positions produced by surface construction.
4. Keep guide U semantics and derive skin samples from each CV position
   - Pros: aligns weights with the generated surface shape while preserving guide-facing U behavior.
   - Cons: requires reconstructing a surface sample from each CV position during build.

## Consequences

Lower-edge surface CVs receive anchor and curl weights from samples that match their generated positions. The code separates anchor field, curl field, and field composition, making future changes to curl strength or falloff easier.

The distinction between guide-facing U and CV-derived skin samples must remain explicit in helper names and documentation.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- Maya runtime validation shows lower-edge CVs should instead preserve upper-edge span/local ownership.
- row ranges or detail placement are intentionally moved to depth-aware distance semantics.
