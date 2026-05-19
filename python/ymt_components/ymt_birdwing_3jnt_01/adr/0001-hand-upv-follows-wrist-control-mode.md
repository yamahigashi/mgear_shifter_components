# ADR-0001: Hand Up-Vector Follows Wrist Control Mode

Status: Proposed
Date: 2026-05-19
Owner: ymtshiftercomponents maintainers
Supersedes: none
Superseded by: none

## Context

`ymt_birdwing_3jnt_01` uses one animator-facing up-vector control for the root/elbow/wrist IK plane. The wrist/hand section has no separate hand up-vector control. The hand IK target can be parented either from the main IK control or from the solved chain through `wristControlMode`.

The previous hidden hand up-vector chain copied `upv_ctl.translate` into a different parent space and then used a hidden aim reference to orient the hand IK handle. That made the hand solve depend on `handChain[0]`, which is also part of the solve result, and duplicated responsibility with the hand IK rotation controls.

## Decision

The hand section will not build a separate hidden hand up-vector chain or aim reference. The visible `upv_ctl` affects the hand section only through `wristControlMode`:

- `IK`: the hand IK target and hand rotation basis stay on the IK control basis, so moving `upv_ctl` does not move the hand IK target.
- `Chain`: the hand IK target and hand rotation basis follow the solved wrist chain, so moving `upv_ctl` affects them through the root/elbow/wrist IK plane.

Final hand orientation remains owned by `handIkRot_ctl` and `handRoll`.

## Considered Options

1. Keep the hidden hand up-vector chain
   - Pros: preserves the previous node layout.
   - Cons: copies local translate values across parent spaces, creates solve-result feedback through `handChain[0]`, and obscures animator-facing control ownership.
2. Add a separate animator-facing hand up-vector control
   - Pros: exposes explicit hand twist control.
   - Cons: contradicts the component requirement that animators see only the shared wing up-vector.
3. Use `wristControlMode` as the hand up-vector policy
   - Pros: matches existing settings, keeps one visible up-vector, and avoids feedback from the solved hand chain.
   - Cons: hand up-vector influence is indirect and must be documented.

## Consequences

The hand solve has fewer hidden dependencies and no longer copies `upv_ctl.translate` into a mismatched local space. Existing rigs that expected hidden hand up-vector twist in `IK` mode will behave differently: in `IK` mode, hand target position and hand rotation basis are independent of `upv_ctl`; in `Chain` mode, they continue to follow the solved wrist basis.

## Confidence and Revisit Trigger

Confidence: Medium

Revisit this ADR when:

- Maya runtime validation shows the `ikSCsolver` needs an explicit hand twist reference.
- A production rig requires an animator-facing hand up-vector or a separate hand up-vector influence setting.
