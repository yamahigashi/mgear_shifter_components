# ADR-0004: Use Local Relative Surface Evaluation

Status: Proposed
Date: 2026-05-20
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_feather_ribbon_01` evaluates its ribbon surface, surface skinning, and rivets as an internal component layer. That layer previously lived under a hidden `noTransform` group with `inheritsTransform` disabled. This avoided some parent transform feedback, but it also made the surface layer escape the component hierarchy and increased the chance of inconsistent behavior when the component root is transformed by a parent rig.

Maya's `skinCluster` and `uvPin` nodes both support local relative evaluation through `relativeSpaceMode = 1`.

## Decision

The hidden surface/rivet layer will stay inside the component transform hierarchy:

- `noTransform.inheritsTransform` remains enabled.
- The ribbon surface skinCluster uses `relativeSpaceMode = 1`.
- Surface rivet `uvPin` nodes use `relativeSpaceMode = 1`.
- Missing `relativeSpaceMode` support is treated as a build error because this component requires local relative surface evaluation.

## Considered Options

1. Keep `noTransform.inheritsTransform = False`
   - Pros: preserves the older world-space escape behavior.
   - Cons: makes the surface layer inconsistent with the component hierarchy and parent rig transforms.
2. Keep inherited transforms but leave skinCluster and uvPin in world/default mode
   - Pros: fewer node attribute changes.
   - Cons: risks double transforms or mixed spaces between the surface, influences, and rivets.
3. Use inherited transforms with local relative skinCluster and uvPin evaluation
   - Pros: keeps surface deformation and rivet outputs in the component's local evaluation space.
   - Cons: requires Maya nodes that expose `relativeSpaceMode` and needs runtime validation in Maya.

## Consequences

The ribbon surface and rivet helpers now evaluate as part of the component transform hierarchy instead of bypassing it. Component-level parent motion should affect the surface layer consistently, while the skinCluster and uvPin nodes compute their outputs in local relative mode.

Existing build environments must provide `relativeSpaceMode` on the relevant Maya nodes. Maya runtime validation is required for scaled, rotated, and mirrored parent component transforms.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- Maya versions without `relativeSpaceMode` need to be supported.
- `noTransform` is renamed to a more accurate surface/rivet root.
- local relative uvPin output requires an explicit relative-space matrix connection in production scenes.
