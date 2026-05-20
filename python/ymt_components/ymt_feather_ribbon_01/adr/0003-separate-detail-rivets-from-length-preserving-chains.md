# ADR-0003: Separate Detail Rivets From Length-Preserving Chains

Status: Proposed
Date: 2026-05-19
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_feather_ribbon_01` detail controls previously used only the first point of each detail chain as the surface-driven driver. Chain direction was then aimed toward a weighted curl-control target. That mixed surface placement, chain length, chain direction, and curl influence in one control hierarchy.

The detail chains need to preserve their segment lengths while still following the ribbon surface direction. Curl controls should contribute rotation offset, not replace the chain aim target.

## Decision

Detail controls will separate surface targets, aim extraction, FK propagation, and rotation offsets:

- Every detail point gets a rivet reference constrained to the ribbon surface, initialized with that point's chain orientation.
- Every detail point also gets an aim reference as a child of its rivet reference. The aim reference inherits rivet translation and initial orientation, and aims toward the next detail point's rivet reference when one exists.
- The final aim reference inherits the previous aim reference rotation because it has no next detail point to aim at.
- Animator-facing detail controls live under a hierarchical FK chain so upstream animator edits propagate to downstream detail controls.
- The FK chain root follows the first rivet reference in translation.
- Aim references provide local rotation to an aim-apply parent inside the FK chain through their local matrix plus the initial offset. Child detail columns use the current aim reference relative to the previous aim reference, so the FK chain receives segment aim deltas instead of repeated absolute aim rotations.
- Curl controls no longer provide aim targets. Their local rotations are blended from nearby curl controls and applied only as curl offsets.
- Curl-to-detail rotation offsets are scaled by animator-facing column multiplier attributes, initialized to `1.0`, after curl-neighborhood blending and before the local curl offset is applied.
- Curl-to-detail rotation propagation converts only the local axis convention: curl `+Z` forward maps to detail `+X` forward, curl `+Y` up maps to detail `-Y` up, and curl `+X` side maps to detail `+Z` side.

## Considered Options

1. Rivet every detail control directly
   - Pros: simple surface following.
   - Cons: does not preserve chain segment lengths.
2. Keep curl controls as aim targets
   - Pros: preserves previous behavior.
   - Cons: curl position controls own chain direction instead of providing curl rotation influence.
3. Separate rivet references and aim references from a hierarchical FK chain
   - Pros: keeps surface position, aim extraction, FK propagation, and curl rotation responsibilities separate.
   - Cons: adds more hidden reference transforms and constraints.

## Consequences

Detail controls preserve their FK chain inheritance while the first point follows the surface and aim references extract surface-derived segment orientation from rivet references. Aim references are children of rivet references, so the rivet provides the stable surface position and initial orientation while the aim reference local matrix carries only the aim delta needed by the aim-apply parent. Downstream aim application subtracts the previous aim reference by matrix inverse before applying the initial offset, matching the hierarchical FK chain. Aim and curl rotations are applied inside the FK chain, but neither curl nor animator offsets feed back into the rivet or aim extraction layers. Curl controls now expose rotation channels and propagate local rotation offsets based on nearby curl weights. The curl rotation offset uses the same curl-neighborhood falloff as surface weighting, but it normalizes curl weights independently and does not reserve influence for anchors. Column multipliers tune how strongly each detail column receives the blended curl rotation without changing the distribution weights themselves.

Maya runtime validation is required for strongly curved chains and for the final point orientation, which inherits from the chain when there is no next rivet target.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- final detail point orientation needs a different fallback than inheriting the previous aim reference.
- chain length preservation needs stretch or soft-length behavior instead of fixed local offsets.
