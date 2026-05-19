# ADR-0001: Size Surface U Subdivisions From Both Edges

Status: Proposed
Date: 2026-05-19
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_feather_ribbon_01` builds its sliding NURBS surface from top anchor positions and lower anchor-end positions. The surface U values are also used by skin weights, curl placement, row ranges, and detail placement.

The previous surface U subdivision count used only the top anchor segment lengths. When lower anchor-end segments were longer than the top edge, the generated NURBS surface had too few CV columns for the lower edge, producing uneven surface density.

## Decision

Surface U parameterization will remain based on the existing top anchor chain. The number of subdivisions per span will be sized from the larger of:

- the top anchor segment length
- the lower anchor-end segment length

This keeps existing U values, row ranges, curl locations, and detail placement semantics stable while ensuring long lower-edge spans receive enough CV columns.

## Considered Options

1. Keep top-edge-only subdivision sizing
   - Pros: preserves previous topology exactly.
   - Cons: undersamples lower-edge spans when feather depth makes the lower edge longer.
2. Reparameterize U from averaged or lower-edge length
   - Pros: could make U distance more uniform across the surface.
   - Cons: changes the meaning of row ranges, curl U, and existing detail placement.
3. Keep top-edge U semantics and size subdivisions from the larger edge
   - Pros: fixes lower-edge undersampling without changing public U semantics.
   - Cons: can add extra CV columns when top and lower edge lengths differ significantly.

## Consequences

Lower-edge-heavy feather ribbon surfaces receive denser U topology where needed. Existing guides retain their U interpretation, but generated surface topology may gain additional columns compared with older builds.

## Confidence and Revisit Trigger

Confidence: High

Revisit this ADR when:

- row ranges or detail placement need arc-length parameterization across the full surface instead of top-edge U semantics.
