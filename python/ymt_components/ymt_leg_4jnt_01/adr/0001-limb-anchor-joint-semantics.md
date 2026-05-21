# ADR-0001: Leg Deformation Joint Control Semantics

Status: Proposed
Date: 2026-05-21
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_leg_4jnt_01` builds two distinct kinds of deformation joints.

The first kind is the primary deformation joint set: `root_jnt`, `knee_jnt`, `ankle_jnt`, and `foot_jnt`. These joints represent the limb segments themselves. Their positions define the anatomical chain and the straight segments between neighboring primary joints.

The second kind is the division deformation joint set. These joints are distributed by the roll spline and exist to provide twist, volume, and in-between deformation support along the limb.

The animator-facing `knee_ctl`, `ankle_ctl`, and `foot_ctl` are deformation-joint controls. They are not only display controls or rig-internal offsets. Their primary role is to shape the corresponding primary deformation joint transform. Their support role is to feed nearby division deformation behavior where that improves roll, twist, volume, and in-between skin deformation.

mGear's stock leg and arm components are useful references for how control transforms can be propagated into deformation support graphs. They are not the source of the primary deformation joint model in `ymt_leg_4jnt_01`; that model is specific to this component.

## Decision

`knee_ctl`, `ankle_ctl`, and `foot_ctl` transforms will define the behavior of the corresponding deformation joints.

Their translation defines the corresponding primary deformation joint position. Their rotation must be reflected in the primary deformation joint orientation and in the support deformation graph where applicable. These controls are not translation-only controls.

For primary limb joints, control world rotation is not itself the joint orientation. The primary limb joint orientation is segment-aware: it is based on the segment aim defined by neighboring primary joint positions, then the control rotation is composed onto that base as a local deformation and twist contribution. In other words, `knee_ctl.rotate`, `ankle_ctl.rotate`, and `foot_ctl.rotate` must not simply replace the orientation generated from the limb chain.

When a primary control translation changes a primary joint position, every primary segment aim orientation that depends on that position must be recomputed from the updated primary joint positions. For example, moving `ankle_ctl` changes the `ankle_jnt` primary position, so the `knee_jnt` segment aim basis from `knee_jnt` to `ankle_jnt` and the `ankle_jnt` segment aim basis from `ankle_jnt` to `foot_jnt` must both update. Existing solved limb joints, guide-derived refs, or other cached orientation sources must not remain the primary orientation source when they no longer match the updated primary joint positions.

Although the named primary deformation joint set is `root_jnt`, `knee_jnt`, `ankle_jnt`, and `foot_jnt`, the `toe` anchor remains the downstream terminal reference for the foot segment. `foot_jnt` orientation is based on the updated `foot_jnt` to `toe` segment aim.

The primary local deformation and twist contribution from a control rotation must be composed after the segment aim basis, in segment-local space. It must not be evaluated as an alternate world-space orientation source.

The primary deformation joint chain must remain a chain of straight segments:

- `root_jnt` to `knee_jnt`
- `knee_jnt` to `ankle_jnt`
- `ankle_jnt` to `foot_jnt`

Division deformation joints remain roll-spline-driven deformation joints. They are separate from the primary deformation joints and must not be used as substitutes for the primary joints.

When implementation changes are made, code should preserve this separation explicitly:

- Primary deformation joint behavior belongs to the primary deformation driver graph.
- Division deformation joint behavior belongs to the roll spline, twist, and volume support graph.
- `knee_ctl`, `ankle_ctl`, and `foot_ctl` transforms must be evaluated as deformation-joint inputs, not as isolated correction offsets.
- Primary limb joint orientation must preserve the segment aim contract. A direct connection from a control world matrix or world rotation to a primary limb joint orientation is incorrect when it bypasses the neighboring-joint segment aim basis.
- A split graph where primary joint translation follows a control but primary joint orientation continues to follow stale `legBones`, guide refs, or cached orientation is also incorrect. Position and orientation must be evaluated from the same updated primary joint chain.
- Control rotation has two distinct outputs: a segment-aware local/twist contribution for primary limb joints, and a support-graph contribution for roll spline, twist, volume, and in-between deformation. These outputs may share the same animator control input, but they are not the same deformation meaning.
- In the division support graph, flip offset attributes are additive support offsets. They must not replace the relevant control rotation contribution unless a later ADR explicitly changes that behavior.

## Considered Options

1. Treat `knee_ctl`, `ankle_ctl`, and `foot_ctl` as isolated correction controls for only the matching joint position.
   - Pros: Preserves the existing limited behavior.
   - Cons: The visible control intent does not match the deformation joint model. Moving or rotating a control does not correctly define the corresponding deformation joint behavior.

2. Treat the roll spline division joints as the authoritative limb shape.
   - Pros: Keeps most deformation interpolation in one system.
   - Cons: Blurs the distinction between primary deformation joints and division deformation joints. Makes joint-relative behavior harder to reason about.

3. Treat `knee_ctl`, `ankle_ctl`, and `foot_ctl` transforms as deformation-joint controls.
   - Pros: Matches the component semantics: primary deformation joints define the limb, division deformation joints support deformation between those primary joints, and the controls feed both roles deliberately.
   - Cons: Requires the implementation to keep primary deformation behavior and division support behavior clearly separated.

Chosen option: option 3.

## Consequences

This gives the component a clearer deformation contract. The primary deformation joints describe the limb chain, while division deformation joints provide secondary deformation support.

Future changes to `ymt_leg_4jnt_01` should be reviewed against this distinction. A fix that only changes division joint interpolation is not sufficient if the bug concerns primary deformation joint movement or orientation. A fix that drives primary deformation joints through division support objects is also suspect, because it reverses the intended dependency direction.

An implementation that directly drives `knee_jnt`, `ankle_jnt`, or `foot_jnt` orientation from the matching control's world rotation changes the meaning of the primary deformation joints and is a design error. It collapses a limb joint into an isolated control transform and can break the straight-segment limb model. The correct implementation must first establish the primary segment aim from neighboring primary joint positions, then compose the control rotation as the intended local deformation or twist contribution.

Runtime validation requires Maya and mGear. Static checks can verify file quality, but the actual behavior must be confirmed by building a leg and moving `knee_ctl`, `ankle_ctl`, and `foot_ctl`.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- The component introduces additional primary deformation joints.
- The roll spline support graph becomes the intended authoritative limb shape.
- Maya validation shows that separating primary deformation behavior from division support cannot satisfy deformation requirements.
