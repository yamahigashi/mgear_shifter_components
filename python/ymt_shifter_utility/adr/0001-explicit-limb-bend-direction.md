# ADR-0001: Explicit Limb Bend Direction

Status: Accepted
Date: 2026-05-18
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

Shoulder connector dummy chains need a stable IK solve plane. Deriving the bend direction from guide elbow placement or from a component normal built from guide positions is unstable because it couples connector behavior to placement artifacts. Some components expose an authored blade convention, and built rigs may expose UPV controls. These are explicit inputs and should be preferred over placement-derived inference.

## Decision

Shared utility code will provide limb bend direction helpers. Components and connectors should use these helpers instead of duplicating local blade, UPV, projection, or normal-generation logic.

The helpers resolve explicit authored inputs in this order:

1. `guide.blades["blade"].y * -1`
2. build-time UPV object position, such as `upv_ctl` or `upv_cns`
3. fail with a clear error

The helpers will project the explicit bend hint onto the relevant chain plane, derive chain normals from the projected bend direction, and will not fall back to elbow placement or `normal + guide.apos` inference.

## Considered Options

1. Compute bend direction from guide positions
   - Pros: Works for components that have no blade or UPV data.
   - Cons: Reintroduces placement-dependent solver plane drift.
2. Require each component to expose a custom `bend_dir`
   - Pros: Clear connector input.
   - Cons: Duplicates convention code across components and makes connector support component-specific.
3. Use shared helpers with explicit blade/UPV inputs
   - Pros: Centralizes the contract and avoids placement-derived inference.
   - Cons: Components without blade or UPV data must be fixed instead of silently building.
4. Keep bend-plane helper logic component-local
   - Pros: Keeps each component self-contained.
   - Cons: Duplicates the blade convention and makes connector behavior easier to drift from component behavior.

## Consequences

Shoulder connector dummy chains use the same authored bend convention as the connected component. Components that need limb solve planes should call the shared helpers so blade convention, UPV fallback, projection, and chain-normal validation remain consistent. Invalid guides now fail early when the explicit bend source is missing or parallel to the chain axis. Existing components that relied on placement-derived behavior may need blade or UPV data to be valid.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- A connector must support a component with no blade or UPV concept.
- The blade axis convention for shoulder-connectable limbs changes.
